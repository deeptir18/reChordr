import sys
import itertools
sys.path.append('..')

# we should go through these and figure out what we need
from common.core import *
from common.audio import *
from common.writer import *
from common.mixer import *
from common.gfxutil import *
from common.wavegen import *
from common.synth import *
from common.clock import *
from common.metro import *
from common.noteseq import *
from common.buffers import *
from common.pitchdetect import *
from input.solo_transcribe import *
from visual.staff_vis import *
from math import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate

from random import randint
import aubio
from bisect import bisect_left
import numpy as np

SET_TEMPO_MODE = 0
SOLO_TRANSCRIBE_MODE = 1
SOLO_EDIT_MODE = 2
CHORD_GENERATION_MODE = 3

class MainWidget(BaseWidget):
	def __init__(self):
		super(MainWidget, self).__init__()
		self.current_mode = SET_TEMPO_MODE

		self.info = topleft_label()
		self.add_widget(self.info)
		
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


	def _init_set_tempo_mode(self):
		# Metronome + rhythm detector
		self.tempo = 60
		self.rhythm_detector = RhythmDetector(self.tempo, rel_rhythm)
		# take AudioScheduler from RhythmDetector
		self.sched = self.rhythm_detector.sched

		# separate audio channel for the metronome
		self.metro_audio = Audio(NUM_CHANNELS)
		self.synth = Synth('../data/FluidR3_GM.sf2', Audio.sample_rate)

		# connect scheduler into audio system
		self.metro_audio.set_generator(self.sched)
		self.sched.set_generator(self.synth)

		# create the metronome:
		self.metro = Metronome(self.sched, self.synth)

	def _init_solo_transcribe_mode(self):
		self.metro.stop()

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

		# used for playback
		self.song = []
		self.note_song = NoteSong(TimeSig(4,4), self.tempo)

		self.seq = NoteSequencer(self.sched, self.synth, 1, (0, 0), self.song, False)

	# Needed for pitch detector
	def receive_audio(self, frames, num_channels) :
			# handle 1 or 2 channel input.
			# if input is stereo, mono will pick left or right channel. This is used
			# for input processing that must receive only one channel of audio (RMS, pitch, onset)
			other = []
			if num_channels == 2:
					mono = frames[0::2] # pick left or right channel
					other = frames[1::2]
			else:
					mono = frames

			# pitch detection: get pitch and display on meter and graph
			self.cur_pitch = self.pitch.write(mono)
			self.pitch_snap.on_update(self.cur_pitch)
			if len(other) > 0:
				self.pitch_snap.on_update(self.pitch.write(other))

	def _init_solo_edit_mode(self):
		self.metro.stop()
		#TODO: an elegant way to process the final note here
		self.on_key_down([None, 'spacebar'], None)
		# render the entire stave but just change parts to be 4 960s
		self.measure_length = 960

		self.playing = False
		self.changing = False
		self.change_idx = 4
		self.change_note = 0

		self.rectangles = []
		
		self.top_stave = TripleStave(Window.height/2)
		# Do we use the bottom stave at all?
		self.bottom_stave = TripleStave(10)
		self.canvas.add(self.top_stave)
		self.canvas.add(self.bottom_stave)
		
		x_pos = NOTES_START
		self.bar_length = (Window.width - NOTES_START)/4.0
		for i in range(4):
				self.canvas.add(Barline(self.top_stave, x_pos))
				self.canvas.add(Barline(self.bottom_stave, x_pos))
				x_pos += self.bar_length

		self.colors = [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 1), (0, 1, 0)]
		self.patches = [(0, 42), (0,41), (0, 40), (0,40), (0, 4)]
		self.parts = ["Bass", "Tenor", "Alto", "Soprano", "Solo"]
		self.num_channels = 5
		self.hi = 0
		# why are lines and self.parts both things?
		lines = ["BASS", "TENOR", "ALTO", "SOPRANO", "solo"]
		single_note_seq = [[960, 0], [960, 0], [960, 0], [960, 0]]
		self.voicing_note_seqs = [single_note_seq for i in lines]
		self.song = kSomewhere # TODO: remove this
		self.voicing_note_seqs[4] = self.song
		# do a sketchy thing to fix the pitch the song
		self.note_staffs = [self.render_note_sequence(self.voicing_note_seqs[i], lines[i], i, self.colors[i]) for i in range(self.num_channels)]
		self.note_sequences = [NoteStaffSequencer(self.sched, self.synth, channel=i+1, patch = self.patches[i],
												 part = self.parts[i], notes = self.voicing_note_seqs[i], loop=True, note_cb=None,
												 note_staffs=self.note_staffs[i]) for i in range(self.num_channels)]

	def _init_chord_generation_mode(self, idx=0):
		self.canvas.clear()
		self.synth.cc(5, 7, 120)
		self.synth.cc(1, 7, 50)
		self.synth.cc(2, 7, 50)
		self.synth.cc(3, 7, 50)
		self.synth.cc(4, 7, 50)

		self.playing = False
		self.changing = False
		self.change_idx = 0
		self.change_note = 0

		self.rectangles = []

		self.top_stave = TripleStave(Window.height/2)
		# Do we use the bottom stave at all?
		self.bottom_stave = TripleStave(10)
		self.canvas.add(self.top_stave)
		self.canvas.add(self.bottom_stave)
		
		x_pos = NOTES_START
		self.bar_length = (Window.width - NOTES_START)/4.0
		for i in range(4):
				self.canvas.add(Barline(self.top_stave, x_pos))
				self.canvas.add(Barline(self.bottom_stave, x_pos))
				x_pos += self.bar_length

		self.colors = [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 1), (0, 1, 0)]
		self.patches = [(0, 42), (0,41), (0, 40), (0,40), (0, 4)]
		self.parts = ["Bass", "Tenor", "Alto", "Soprano", "Solo"]
		self.num_channels = 5
		
		lines = ["BASS", "TENOR", "ALTO", "SOPRANO", "solo"]
		self.voicing_options = get_chords_and_voicings(self.song, self.measure_length)
		self.voicing_note_seqs = self.voicing_options[idx]
		self.voicing_note_seqs = [list(self.voicing_note_seqs[i]) for i in lines]
		self.note_staffs = [self.render_note_sequence(self.voicing_note_seqs[i], lines[i], i, self.colors[i]) for i in range(self.num_channels)]
		self.note_sequences = [NoteStaffSequencer(self.sched, self.synth, channel=i+1, patch = self.patches[i],
													 part = self.parts[i], notes = self.voicing_note_seqs[i], loop=True, note_cb=None, 
													 note_staffs=self.note_staffs[i]) for i in range(self.num_channels)]

	# Needed for solo edit and chord
	def render_note_sequence(self, seq, note_type, part_idx, color): # renders a 4 bar note sequence
		self.time_passed = 0.
		self.note_staffs = []
		note_idx = 0
		pitches = []
		for note in seq:
			length = note[0]
			start = (self.time_passed/(960*4.0))*(Window.width - NOTES_START) + NOTES_START
			end = start + length/(960*4.0)*(Window.width - NOTES_START)

			pitch = note[1]
			pitches.append(pitch)
			note = StaffNote(pitch, self.top_stave, start, end, note_type, color, part_idx, note_idx)
			# are these things not the same?
			self.rectangles.append(note)
			self.note_staffs.append(note)
			self.canvas.add(note)
			self.time_passed += length
			note_idx += 1
		return self.note_staffs

	#NEEDS ALTERING: same as on_touch_down, currently splits the screen into 5 parts vertically and you can change parts that way
	def find_part(self, pos):
		(x, y) = pos
		corners = [r.rect_corners() for r in self.rectangles]
		for ((x1, x2, y1, y2), part_idx, note_idx) in corners:
			if x1 <= x and x <= x2 and y1 <= y and y <= y2:
				return (part_idx, note_idx)
		return None

	def on_update(self):
		if self.current_mode == SET_TEMPO_MODE:
			self.metro_audio.on_update()
			self.info.text = "Welcome to reChordr\nUse the left/right arrows to pick a tempo\n"
			self.info.text += "Current tempo: %d\n" % self.tempo
			self.info.text += "Press 'N' to go to the next step"
		elif self.current_mode == SOLO_TRANSCRIBE_MODE:
			self.metro_audio.on_update()
			self.pitch_detect_audio.on_update()
			self.info.text = "Welcome to reChordr\n"
			self.info.text += "Press 1 to toggle metronome at tempo %d\n" % self.tempo
			self.info.text += "Sing and tap the spacebar at the start of each note\n"
			self.info.text += "Press 2 to play transcribed notes\n"
			self.info.text += "Press 'S' to start over\n"
			self.info.text += "Press 'N' to go to the next step"
		elif self.current_mode == SOLO_EDIT_MODE:
			self.metro_audio.on_update()
			self.info.text = "Welcome to reChordr\n"
			self.info.text += "Press 2 to play transcribed notes\n"
			self.info.text += "Do something to edit\n"
			self.info.text += "Press 'N' to go to the next step"
		elif self.current_mode == CHORD_GENERATION_MODE:
			self.info.text = "Welcome to reChordr\n"
			self.info.text += "Press the spacebar to play your piece\n"
			self.info.text += "Do something to edit\n"
			self.info.text += "Press 'N' to go to the next step"

			if self.playing:
				self.metro_audio.on_update()
			if self.changing:
				self.info.text += "Changing: " + self.parts[self.change_idx]

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
				self.metro.start()

		elif self.current_mode == SOLO_TRANSCRIBE_MODE:
			# turn metronome on/off
			if keycode[1] == '1':
					self.metro.toggle()

			# turn sequencer on/off
			if keycode[1] == '2':
					self.on_key_down([None, 'spacebar'], None)
					self.song = trim_notes_for_playback(self.song)
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
						self.song.append((int(duration), int(pitch)))

			# start over recording
			if keycode[1] == 's':
				# re-initialize all of these
				# this seems hack-y since it's copy pasting bits of other methods
				self.rhythm_detector = RhythmDetector(self.tempo, rel_rhythm)
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
				self.changing = False
				self.playing = not self.playing
				for ns in self.note_sequences:
					ns.toggle()

			# start playback
			if keycode[1] == 's':
				if not self.playing:
					self.playing = True
					for ns in self.note_sequences:
						ns.start()

			# change notes
			if keycode[1] == 'c':
				if not self.playing:
					self.changing = not self.changing
				if self.changing:
					if self.current_mode == SOLO_EDIT_MODE:
						self.change_note = self.note_sequences[4].current_note_index()
						self.change_note %= len(self.note_sequences[4].get_notes())
					else:
						self.change_note = self.note_sequences[self.change_idx].current_note_index()
						self.change_note %= len(self.note_sequences[self.change_idx].get_notes())
					self.note_sequences[self.change_idx].highlight(self.change_note)
				else:
					self.note_sequences[self.change_idx].un_highlight(self.change_note)

			# change note pitch up or down
			if keycode[1] == 'up':
				pitch = self.note_sequences[self.change_idx].get_cur_pitch(self.change_note)
				# this seems like something that could be accomplished with the Key class
				new_pitch =  self.bottom_stave.get_pitch_up(pitch)
				self.note_staffs[self.change_idx][self.change_note].set_note(new_pitch)
				#move note up from change_idx
				self.note_sequences[self.change_idx].set_note(new_pitch, self.change_note)

			if keycode[1] == 'down':
				if self.changing:
					pitch = self.note_sequences[self.change_idx].get_cur_pitch(self.change_note)
					new_pitch =  self.bottom_stave.get_pitch_down(pitch)
					#print "down", self.change_note, pitch, new_pitch
					self.note_staffs[self.change_idx][self.change_note].set_note(new_pitch)
					#move note up from change_idx
					self.note_sequences[self.change_idx].set_note(new_pitch, self.change_note)

			# scan through notes left or right
			if keycode[1] == 'left':
				if self.changing:
					self.note_sequences[self.change_idx].un_highlight(self.change_note)
					self.change_note -= 1
					self.change_note %= len(self.note_sequences[self.change_idx].get_notes())
					self.note_sequences[self.change_idx].highlight(self.change_note)

			if keycode[1] == 'right':
				if self.changing:
					self.note_sequences[self.change_idx].un_highlight(self.change_note)
					self.change_note += 1
					self.change_note %= len(self.note_sequences[self.change_idx].get_notes())
					self.note_sequences[self.change_idx].highlight(self.change_note)

		if self.current_mode == CHORD_GENERATION_MODE:
			o = lookup(keycode[1], '1234', '0123')
			if o:
				self._init_chord_generation_mode(int(o))


	def on_touch_down(self, touch):
		c = None
		if self.current_mode == SOLO_EDIT_MODE or self.current_mode == CHORD_GENERATION_MODE:
			if self.changing:
				c = self.find_part(touch.pos)
			if c:
				self.note_sequences[self.change_idx].un_highlight(self.change_note)
				(self.change_idx, self.change_note) = c
				self.note_sequences[self.change_idx].highlight(self.change_note)
		else:
			pass


run(MainWidget)
