import sys
import itertools
sys.path.append('..')

from common.core import *
from common.audio import *
from common.writer import *
from common.mixer import *
from common.gfxutil import *
from common.synth import *
from common.clock import *
from common.metro import *
from common.noteseq import *
from common.buffers import *
from common.pitchdetect import *
from common.constants import *
from input.solotranscribe import *
from input.harmonycreator import *
from visual.staffvis import *
from math import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.label import Label

class MainWidget(BaseWidget):
	def __init__(self):
		super(MainWidget, self).__init__()
		Window.clearcolor = (1, 1, 1, 1)
		self.current_mode = SET_TEMPO_MODE
		self.info = topleft_label()
		print self.top
		#self.add_widget(self.info)

		#self.canvas.add(Rectangle(pos=(0, Window.height - 10), size=(200, 40), source='./visual/logo.png'))

		self._init_set_tempo_mode()

	def _change_modes(self):
		if self.current_mode == SET_TEMPO_MODE:
			self._init_solo_transcribe_mode()
			self.current_mode = SOLO_TRANSCRIBE_MODE
		elif self.current_mode == SOLO_TRANSCRIBE_MODE:
			self._init_solo_edit_mode()
			self.current_mode = SOLO_EDIT_MODE
		elif self.current_mode == SOLO_EDIT_MODE:
			self._init_chord_generation_mode()
			self.current_mode = CHORD_GENERATION_MODE

	####################
	# Set Tempo Mode   #
	####################
	def _init_set_tempo_mode(self):
		# Metronome + rhythm detector
		self.tempo = DEFAULT_TEMPO
		self.rhythm_detector = RhythmDetector(self.tempo, RHYTHM_PROFILE)
		# take AudioScheduler from RhythmDetector
		self.sched = self.rhythm_detector.sched

		# separate audio channel for the metronome
		self.metro_audio = Audio(NUM_CHANNELS)
		self.synth = Synth(PATH_TO_SYNTH, Audio.sample_rate)

		# connect scheduler into audio system
		self.metro_audio.set_generator(self.sched)
		self.sched.set_generator(self.synth)

		# create the metronome:
		self.metro = Metronome(self.sched, self.synth, METRO_CHANNEL)
		self.metro.start()
		self.canvas.clear()
		self.canvas.add(Rectangle(pos=(0,Window.height - 672), size=(Window.width, 672), source='./visual/set_tempo_mode.png'))
		self.label = Label(text = str(self.tempo), valign='top', font_size='100sp',
              pos=(Window.width * 0.7, Window.height * -0.2),
              text_size=(Window.width, Window.height))
		self.label.color = (0, 0, 0, 1)
		self.add_widget(self.label)
	##########################
	# Solo Transcribe Mode   #d
	##########################
	def _init_solo_transcribe_mode(self):
		self.metro.stop()
		self.canvas.clear()
		self.canvas.add(Rectangle(pos=(0,Window.height - 1087), size=(Window.width, 987), source='./visual/solo_transcribe_mode.png'))

		# Pitch detector
		self.pitch_detect_audio = Audio(NUM_CHANNELS, input_func=self.receive_audio)
		self.mixer = Mixer()
		self.pitch_detect_audio.set_generator(self.mixer)
		self.io_buffer = IOBuffer()
		self.mixer.add(self.io_buffer)
		self.pitch = PitchDetector()

		# Pitch snap
		self.pitch_snap = PitchSnap()
		self.last_pitch = Pitch(0, 1, 0, 0, None)

		self.top_song = []
		self.bottom_song = []

		# used for playback
		# argument for NoteSequencer
		self.song = []
		# holds information about pitch detection confidence
		self.note_song = NoteSong(TimeSig(4,4), self.tempo)

		# NoteSequencer with self.song as argument
		self.seq = NoteSequencer(self.sched, self.synth, 1, (0, 0), self.song, False)

	# Helper method for pitch detector
	def receive_audio(self, frames, num_channels) :
			# handle 1 or 2 channel input.
			# if input is stereo, mono will pick left or right channel. This is used
			# for input processing that must receive only one channel of audio (RMS, pitch, onset)

			# other channel data if stereo
			other = []
			if num_channels == 2:
					mono = frames[0::2] # pick left or right channel
					other = frames[1::2]
			else:
					mono = frames

			# pitch detection: get pitch
			cur_pitch = self.pitch.write(mono)
			self.pitch_snap.on_update(cur_pitch)
			# use both channels to help detect pitch
			if len(other) > 0:
				self.pitch_snap.on_update(self.pitch.write(other))

	####################
	# Solo Edit Mode   #
	####################
	def _init_solo_edit_mode(self):
		self.canvas.clear()
		self.canvas.add(Rectangle(pos=(40,Window.height - 260), size=(Window.width - 40, 210), source='./visual/solo_edit_mode.png'))
		self.metro.stop()
		self.seq.stop()
		#TODO: an elegant way to process the final note here
		# render the entire stave but just change parts to be 4 measures

		# variables for playback + editing
		self.playing = False
		self.changing = False
		# which part is being changed
		self.change_idx = 4
		# idx of note within the part that's being changed
		self.change_note = 0

		self.top_stave = TripleStave(Window.height/2)
		# Do we use the bottom stave at all?
		self.bottom_stave = TripleStave(100)
		self.canvas.add(Color(0, 0, 0, 1))
		self.canvas.add(self.top_stave)
		self.canvas.add(self.bottom_stave)

		barlines = get_all_barlines([self.top_stave, self.bottom_stave])
		for b in barlines:
			self.canvas.add(b)

		# gives empty voicings for SATB parts
		single_note_seq = [[MEASURE_LENGTH, 0], [MEASURE_LENGTH, 0], [MEASURE_LENGTH, 0], [MEASURE_LENGTH, 0]]
		self.song = TEST_SONG2# TODO: remove this
		
		self.song = trim_notes_for_playback(self.song)
		print self.song
		# transpose self.song
		self.song = transpose_song(self.song)
		self.song = trim_to_measures(self.song, MEASURE_LENGTH, 8)[0]
		print self.song

		self.top_song, self.bottom_song = trim_to_measures(self.song, MEASURE_LENGTH, 4)

		# four different chord/voicing options as part: NoteSequencer data form
		#self.voicing_options = get_chords_and_voicings(self.song, MEASURE_LENGTH)
		top_voicings = get_chords_and_voicings(self.top_song, MEASURE_LENGTH)
		bottom_voicings = get_chords_and_voicings(self.bottom_song, MEASURE_LENGTH)
		# turn this into the following:
		# array of SATB + solo line, each in (dur, midi) form
		top_note_seqs = [single_note_seq for i in PARTS]
		top_note_seqs[4] = self.top_song

		bottom_note_seqs = [single_note_seq for i in PARTS]
		bottom_note_seqs[4] = self.bottom_song

		self.staff_note_parts = []
		for i in range(NUM_PARTS):
			top = get_staff_notes(top_note_seqs[i], PARTS[i], 0, i, COLORS[i], self.top_stave)
			bottom = get_staff_notes(bottom_note_seqs[i], PARTS[i], len(top), i, COLORS[i], self.bottom_stave)
			self.staff_note_parts.append(top + bottom)

		# do a sketchy thing to fix the pitch the song
		# array of SATB + solo line, each as a collection of StaffNote objects
		for part in self.staff_note_parts:
			for staff_note in part:
				self.canvas.add(staff_note)

		# array of SATB + solo line, each a NoteSequencer object
		self.note_sequencers = [NoteSequencer(self.sched, self.synth, channel=PART_CHANNELS[i], patch = PATCHES[i],
												 								 notes = top_note_seqs[i] + bottom_note_seqs[i], loop=True, note_cb=highlight_staff_note,
												 								 cb_args = self.staff_note_parts[i]) for i in range(NUM_PARTS)]

	def _init_chord_generation_mode(self, idx=0):
		self.canvas.clear()
		self.canvas.add(Rectangle(pos=(40,Window.height - 260), size=(Window.width - 40, 210), source='./visual/solo_edit_mode.png'))
		self.song = self.note_sequencers[4].notes
		for ns in self.note_sequencers:
			ns.stop()

		# set volumes
		for i in range(NUM_PARTS):
			self.synth.cc(PART_CHANNELS[i], 7, PART_VOLUMES[i])

		# variables for playback + editing
		self.playing = False
		self.changing = False
		# which part is being changed
		self.change_idx = 4
		# idx of note within the part that's being changed
		self.change_note = 0

		self.canvas.add(Color(0, 0, 0, 1))
		self.canvas.add(self.top_stave)
		self.canvas.add(self.bottom_stave)

		barlines = get_all_barlines([self.top_stave, self.bottom_stave])
		for b in barlines:
			self.canvas.add(b)

		self.top_song, self.bottom_song = trim_to_measures(self.song, MEASURE_LENGTH, 4)
		print self.top_song, self.bottom_song

		# four different chord/voicing options as part: NoteSequencer data form
		#self.voicing_options = get_chords_and_voicings(self.song, MEASURE_LENGTH)
		top_voicings = get_chords_and_voicings(self.top_song, MEASURE_LENGTH)
		bottom_voicings = get_chords_and_voicings(self.bottom_song, MEASURE_LENGTH)
		# turn this into the following:
		# array of SATB + solo line, each in (dur, midi) form
		top_note_seqs = top_voicings[idx % len(top_voicings)]
		top_note_seqs = [list(top_note_seqs[i]) for i in PARTS]

		bottom_note_seqs = bottom_voicings[idx % len(bottom_voicings)]
		bottom_note_seqs = [list(bottom_note_seqs[i]) for i in PARTS]
		#voicing_note_seqs = self.voicing_options[idx]
		#voicing_note_seqs = [list(voicing_note_seqs[i]) for i in PARTS]
		# array of SATB + solo line, each as a collection of StaffNote objects
		self.staff_note_parts = []
		for i in range(NUM_PARTS):
			top = get_staff_notes(top_note_seqs[i], PARTS[i], 0, i, COLORS[i], self.top_stave)
			bottom = get_staff_notes(bottom_note_seqs[i], PARTS[i], len(top), i, COLORS[i], self.bottom_stave)
			self.staff_note_parts.append(top + bottom)

		for part in self.staff_note_parts:
			for staff_note in part:
				self.canvas.add(staff_note)

		# array of SATB + solo line, each a NoteSequencer object
		self.note_sequencers = [NoteSequencer(self.sched, self.synth, channel=PART_CHANNELS[i], patch = PATCHES[i],
												 								 notes = top_note_seqs[i] + bottom_note_seqs[i], loop=True, note_cb=highlight_staff_note,
												 								 cb_args = self.staff_note_parts[i]) for i in range(NUM_PARTS)]

	# returns which StaffNote was clicked
	def find_part(self, pos):
		for part in self.staff_note_parts:
			for staff_note in part:
				if staff_note.intersects(pos):
					return (staff_note.part_idx, staff_note.note_idx)
		return None

	def on_update(self):
		# Set text
		if self.current_mode == SET_TEMPO_MODE:
			self.metro_audio.on_update()
		elif self.current_mode == SOLO_TRANSCRIBE_MODE:
			self.metro_audio.on_update()
			self.pitch_detect_audio.on_update()
		elif self.current_mode == SOLO_EDIT_MODE:
			self.metro_audio.on_update()
			self.info.text = "Welcome to reChordr"
			self.info.text += '\nfps:%d' % kivyClock.get_fps()
		else:# self.current_mode == CHORD_GENERATION_MODE:
			self.metro_audio.on_update()
			self.info.text = "Welcome to reChordr"
			self.info.text += '\nfps:%d' % kivyClock.get_fps()

	def on_key_down(self, keycode, modifiers):
		if keycode[1] == 'n':
			self._change_modes()

		if self.current_mode == SET_TEMPO_MODE:
			# adjust tempo
			tempo_ctrl = lookup(keycode[1], ('left', 'right'), (-5, 5))
			if tempo_ctrl:
				self.tempo += tempo_ctrl
				self.rhythm_detector.set_tempo(self.tempo)

				self.sched = self.rhythm_detector.sched
				# connect scheduler into audio system
				self.metro_audio.set_generator(self.sched)
				self.sched.set_generator(self.synth)

				self.metro = Metronome(self.sched, self.synth)
				self.label.text = str(self.tempo)
				self.metro.start()

		elif self.current_mode == SOLO_TRANSCRIBE_MODE:
			# turn metronome on/off
			if keycode[1] == 'm':
					self.metro.toggle()

			# turn sequencer on/off
			if keycode[1] == 'p':
					self.on_key_down([None, 'spacebar'], None)
					self.song = trim_to_measures(trim_notes_for_playback(self.song), MEASURE_LENGTH, 8)[0]
					self.seq.notes = self.song
					self.seq.toggle()

			# marks the beginning of each note
			if keycode[1] == 'spacebar':
					self.rhythm_detector.add_note()
					self.pitch_snap.snap_pitch()
					if len(self.rhythm_detector.durations) > 0:
						duration = self.rhythm_detector.durations[-1]
						abs_pitch = self.pitch_snap.abs_pitches[-1]
						rel_pitch = self.pitch_snap.rel_pitches[-1]
						pitch_obj = Pitch(abs_pitch[0], abs_pitch[1], rel_pitch[0], rel_pitch[1], self.last_pitch)
						pitch = pitch_obj.get_best_guess()
						self.last_pitch = pitch_obj
						noteinfo = NoteInfo(pitch_obj, duration)
						self.note_song.add_to_solo_voice(noteinfo)
						self.song.append([int(duration), int(pitch)])

			# start over recording
			if keycode[1] == 's':
				# re-initialize all of these
				# this seems hack-y since it's copy pasting bits of other methods
				self.rhythm_detector = RhythmDetector(self.tempo, RHYTHM_PROFILE)
				self.sched = self.rhythm_detector.sched
				# connect scheduler into audio system
				self.metro_audio.set_generator(self.sched)
				self.sched.set_generator(self.synth)

				self.metro = Metronome(self.sched, self.synth)

				self.pitch_snap = PitchSnap()
				self.last_pitch = Pitch(0, 1, 0, 0, None)

				# used for playback
				self.song = []
				self.note_song = NoteSong(TimeSig(4,4), self.tempo)
				self.seq = NoteSequencer(self.sched, self.synth, 1, (0, 0), self.song, False)

		elif self.current_mode == CHORD_GENERATION_MODE or self.current_mode == SOLO_EDIT_MODE:

			# toggle playback
			if keycode[1] == 'p':
				for part in self.staff_note_parts:
					reset_to_default(part)
				self.changing = False
				self.playing = not self.playing
				for ns in self.note_sequencers:
					# currently plays from the beginning
					ns.toggle()

			# change notes
			if keycode[1] == 'c':
				for part in self.staff_note_parts:
					reset_to_default(part)
				self.playing = False
				for ns in self.note_sequencers:
					# currently plays from the beginning
					ns.stop()
				self.changing = not self.changing
				if self.changing:
					# TODO: have it from the current place?
					self.change_note = 0
					# if self.current_mode == SOLO_EDIT_MODE:
						# self.change_note = self.note_sequences[4]
						# self.change_note %= len(self.note_sequences[4].note_sequencer.notes)
					# else:
					# 	self.change_note = self.note_sequences[self.change_idx].current_note_index()
					# 	self.change_note %= len(self.note_sequences[self.change_idx].get_notes())
					self.staff_note_parts[self.change_idx][self.change_note].set_highlight(True)
				else:
					self.staff_note_parts[self.change_idx][self.change_note].set_highlight(False)

			# change note pitch up or down
			if keycode[1] == 'up':
				if self.changing:
					staff_note = self.staff_note_parts[self.change_idx][self.change_note]
					# use a method to just move this staff note up one semitone -> takes care of pitch and sharps
					pitch = staff_note.pitch
					if staff_note.check_pitch(pitch + 1):
						new_pitch = pitch + 1
						staff_note.set_pitch(new_pitch)
						#move note up from change_idx
						self.note_sequencers[self.change_idx].set_pitch(new_pitch, self.change_note)

			if keycode[1] == 'down':
				if self.changing:
					staff_note = self.staff_note_parts[self.change_idx][self.change_note]
					pitch = staff_note.pitch
					if staff_note.check_pitch(pitch - 1):
					# if (pitch - 1) >= MIN_PITCH:
					# this seems like something that could be accomplished with the Key class
						new_pitch =  pitch - 1
						staff_note.set_pitch(new_pitch)
						#move note up from change_idx
						self.note_sequencers[self.change_idx].set_pitch(new_pitch, self.change_note)

			# scan through notes left or right
			scan = lookup(keycode[1], ['left', 'right'], [-1, 1])
			if scan:
				if self.changing:
					self.staff_note_parts[self.change_idx][self.change_note].set_highlight(False)
					self.change_note += scan
					self.change_note %= len(self.staff_note_parts[self.change_idx])
					self.staff_note_parts[self.change_idx][self.change_note].set_highlight(True)

		if self.current_mode == CHORD_GENERATION_MODE:
			o = lookup(keycode[1], '1234', '0123')
			if o:
				self._init_chord_generation_mode(int(o))


	def on_touch_down(self, touch):
		c = None
		if self.current_mode == SOLO_EDIT_MODE or self.current_mode == CHORD_GENERATION_MODE:
			c = self.find_part(touch.pos)
			if c:
				if not self.changing:
					# enter changing mode
					self.on_key_down([None, 'c'], None)
				self.staff_note_parts[self.change_idx][self.change_note].set_highlight(False)
				(self.change_idx, self.change_note) = c
				self.staff_note_parts[self.change_idx][self.change_note].set_highlight(True)
		else:
			pass

run(MainWidget)
