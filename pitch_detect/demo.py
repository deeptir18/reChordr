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
		elif self.current_mode == CHORD_GENERATION_MODE:
			self._init_rhythm_edit_mode()
			self.current_mode = RHYTHM_EDIT_MODE

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
		top_voicings, top_chords, top_key = get_chords_and_voicings(self.top_song, MEASURE_LENGTH)
		bottom_voicings, bottom_chords, bottom_key = get_chords_and_voicings(self.bottom_song, MEASURE_LENGTH)
		# turn this into the following:
		# array of SATB + solo line, each in (dur, midi) form
		self.top_note_seqs = top_voicings[idx % len(top_voicings)]
		self.top_note_seqs = [list(self.top_note_seqs[i]) for i in PARTS]
		self.chord_progression = []
		for i in range(len(top_chords[idx])):
			self.chord_progression.append(top_chords[idx][i])

		for i in range(len(bottom_chords[idx])):
			self.chord_progression.append(bottom_chords[idx][i])

		# print "Length of chord is {} and {}".format(len(self.chord_progression), self.chord_progression)
		self.key = top_key
		self.bottom_note_seqs = bottom_voicings[idx % len(bottom_voicings)]
		self.bottom_note_seqs = [list(self.bottom_note_seqs[i]) for i in PARTS]
		#voicing_note_seqs = self.voicing_options[idx]
		#voicing_note_seqs = [list(voicing_note_seqs[i]) for i in PARTS]
		# array of SATB + solo line, each as a collection of StaffNote objects
		self.staff_note_parts = []
		for i in range(NUM_PARTS):
			self.top_thing = get_staff_notes(self.top_note_seqs[i], PARTS[i], 0, i, COLORS[i], self.top_stave)
			self.bottom_thing = get_staff_notes(self.bottom_note_seqs[i], PARTS[i], len(self.top_thing), i, COLORS[i], self.bottom_stave)
			self.staff_note_parts.append(self.top_thing + self.bottom_thing)

		for part in self.staff_note_parts:
			for staff_note in part:
				self.canvas.add(staff_note)

		# array of SATB + solo line, each a NoteSequencer object
		self.note_sequencers = [NoteSequencer(self.sched, self.synth, channel=PART_CHANNELS[i], patch = PATCHES[i],
												 								 notes = self.top_note_seqs[i] + self.bottom_note_seqs[i], loop=True, note_cb=highlight_staff_note,
												 								 cb_args = self.staff_note_parts[i]) for i in range(NUM_PARTS)]

	##########################
	# Rhythm Edit Mode  #
	##########################
	def _init_rhythm_edit_mode(self):
		# print "In rhythm edit mode!!!!!!!!"
		self.canvas.clear()
		for ns in self.note_sequencers:
			ns.stop()

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

		# we still have access to last voicing note seq -> this is the one the user chose
		# array of SATB + solo line, each as a collection of StaffNote objects
		self.staff_note_parts = []
		for i in range(NUM_PARTS):
			self.top_thing = get_staff_notes(self.top_note_seqs[i], PARTS[i], 0, i, COLORS[i], self.top_stave)
			self.bottom_thing = get_staff_notes(self.bottom_note_seqs[i], PARTS[i], len(self.top_thing), i, COLORS[i], self.bottom_stave)
			self.staff_note_parts.append(self.top_thing + self.bottom_thing)

		for part in self.staff_note_parts:
			for staff_note in part:
				self.canvas.add(staff_note)


		# array of SATB + solo line, each a NoteSequencer object
		self.note_sequencers = [NoteSequencer(self.sched, self.synth, channel=PART_CHANNELS[i], patch = PATCHES[i],
												 								 notes = self.top_note_seqs[i] + self.bottom_note_seqs[i], loop=True, note_cb=highlight_staff_note,
												 								 cb_args = self.staff_note_parts[i]) for i in range(NUM_PARTS)]


		# have a boolean which tells you if this bar is rhythmed and which rhythm template it is
		self.rhythm_templates = []
		for i in range(len(self.note_sequencers)):
			rhythm_templates= [0]*4
			self.rhythm_templates.append(rhythm_templates)# default, everyone is whole notes
		# print self.rhythm_templates

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
		elif self.current_mode == CHORD_GENERATION_MODE:
			self.metro_audio.on_update()
			self.info.text = "Welcome to reChordr"
			self.info.text += '\nfps:%d' % kivyClock.get_fps()
		elif self.current_mode == RHYTHM_EDIT_MODE:
			self.metro_audio.on_update()
			self.info.text = "Welcome to reChordr. Edit those rhythms!\n"

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


		elif self.current_mode == RHYTHM_EDIT_MODE:
			# toggle playback
			if keycode[1] == 'p':
				for part in self.staff_note_parts:
					reset_to_default(part)
				self.changing = False
				self.playing = not self.playing
				for ns in self.note_sequencers:
					# currently plays from the beginning
					ns.toggle()

			# for cycling in between rhythm options
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

				# print "self.changing_note is {}".format(self.change_note)

			if keycode[1] == "right":
				if not self.changing:
					print "No rhythm options to cycle between"
				else:
					# cycle through the rhythm options with the right key
					if PARTS[self.change_idx] != SOLO: # disable arpeggios on solo edit mode
						current_bar = self.get_current_bar()
						# print "CURRENT BAR is {}".format(current_bar)
						# print "Rhythm temps {}".format(self.rhythm_templates)
						# print "CHANGE ID {}, change note {}".format(self.change_idx, self.change_note)
						current_rhythm_template_index = self.rhythm_templates[self.change_idx][current_bar]
						self.rhythm_templates[self.change_idx][current_bar] = (current_rhythm_template_index + 1)%len(TEST_RHYTHM_TEMPLATES)
						midi = self.note_sequencers[self.change_idx].get_song()[self.change_note][1]
						particular_chord = self.chord_progression[current_bar]
						# print "Rhythm temp index is {}".format(self.rhythm_templates[self.change_idx][current_bar])
						# print "RHythm temp is {}".format(TEST_RHYTHM_TEMPLATES[self.rhythm_templates[self.change_idx][current_bar]])

						rhythm_template = RhythmTemplate(TEST_RHYTHM_TEMPLATES[self.rhythm_templates[self.change_idx][current_bar]])
						# print rhythm_template, "rhythm_template"
						measure = rhythm_template.create_bar(particular_chord, self.key, midi)

						self.replace_staff_note_with_rhythm(measure, current_bar)

						self.changing = False

				# get the rhythm options for this change note

		if self.current_mode == CHORD_GENERATION_MODE:
			o = lookup(keycode[1], '1234', '0123')
			if o:
				self._init_chord_generation_mode(int(o))


	def on_touch_down(self, touch):
		c = None
		if self.current_mode == SOLO_EDIT_MODE or self.current_mode == CHORD_GENERATION_MODE or self.current_mode == RHYTHM_EDIT_MODE:
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

	def get_current_bar(self):
		# get the current bar depending on the change_note
			FULL_TIME = MEASURE_LENGTH * 4
			time = 0
			current_song = self.note_sequencers[self.change_idx].get_song()
			for i in range(len(current_song)):
				length = current_song[i][0]
				if i <= self.change_note:
					time += length

			# percent passed
			percent_passed = float(time)/FULL_TIME
			if percent_passed <= .25:
				return 0
			elif percent_passed <= .5:
				return 1
			elif percent_passed <= .75:
				return 2
			else:
				return 3


	def replace_staff_note_with_rhythm(self, replacement, current_bar):
		"""
		This method replaces what is currently the note sequence with some rhythm sequence.
		It's sort of hacky, because it gets the new song from the current note sequencer "replace song at index" function,
		but then creates a new note sequencer
		"""
		# replaces the given whole note with a replacement rhythmed version of that whole note
		# replace the notes in the parts
		top = False
		if current_bar < 4: # changing the first bars
			top = True

		for staff_note in self.staff_note_parts[self.change_idx]:
			self.canvas.remove(staff_note)
		# print "Song was {}".format(self.note_sequencers[self.change_idx].get_song())
		self.note_sequencers[self.change_idx].replace_song_at_index(self.change_note, replacement, MEASURE_LENGTH, current_bar)
		# print "Song now is {}".format(self.note_sequencers[self.change_idx].get_song())
		# remove the staff note and insert new staff notes at the right location
		self.top_note_seqs[self.change_idx] = self.note_sequencers[self.change_idx].get_half_melody(True)
		self.bottom_note_seqs[self.change_idx] = self.note_sequencers[self.change_idx].get_half_melody(False)

		self.top_thing = get_staff_notes(self.top_note_seqs[self.change_idx], PARTS[self.change_idx], 0, self.change_idx, COLORS[self.change_idx], self.top_stave)
		self.bottom_thing = get_staff_notes(self.bottom_note_seqs[self.change_idx], PARTS[self.change_idx], len(self.top_thing), self.change_idx, COLORS[self.change_idx], self.bottom_stave)
		self.staff_note_parts[self.change_idx] = self.top_thing + self.bottom_thing
		# print self.staff_note_parts[self.change_idx]
		for staff_note in self.staff_note_parts[self.change_idx]:
			self.canvas.add(staff_note)

		# # add it back in using the new note sequencer
		# new_note_seq = self.note_sequencers[self.change_idx].get_song()
		# self.note_sequencers[self.change_idx] = new_note_seq

		# TODO: should be able to just replace the CB ARGS to do this properly
		# self.note_sequencers[self.change_idx].replace_cb_args(self.staff_note_parts[self.change_idx])

		# or just replace the whole note sequencer
		# TODO: unsure why we need to replace the whole note sequencer - something is wrong with the highlight callback
		self.note_sequencers[self.change_idx] = NoteSequencer(self.sched, self.synth, channel=PART_CHANNELS[self.change_idx], patch = PATCHES[self.change_idx],
												 								 notes = self.top_note_seqs[self.change_idx] + self.bottom_note_seqs[self.change_idx], loop=True, note_cb=highlight_staff_note,
												 								 cb_args = self.staff_note_parts[self.change_idx])
		# unhighlight everything?
		for i in range(len(self.staff_note_parts[self.change_idx])):
			self.staff_note_parts[self.change_idx][i].set_highlight(False)

run(MainWidget)
