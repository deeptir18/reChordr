#####################################################################
#
# input_demo.py
#
# Copyright (c) 2017, Eran Egozy
#
# Released under the MIT License (http://opensource.org/licenses/MIT)
#
#####################################################################

# contains example code for some simple input (microphone) processing.
# Requires aubio (pip install aubio).

import sys
sys.path.append('..')

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
from math import *
from noteclass import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate

from random import randint
import aubio
from bisect import bisect_left
import numpy as np

NUM_CHANNELS = 2


rel_rhythm = [2.5, 2.5, 2.5, 3.7, 4.5, 4.5, 7.7, 7.7, 8.3, 9.5, 9.5, 9.5]
beat_rhythm = [2.5, 2.5, 2.5, 3.7, 4.5, 4.5, 7.7, 7.7, 8.5, 9.7, 9.7, 9.7]

class RhythmDetector(object):
    def __init__(self, tempo, rhythm_profile):
        super(RhythmDetector, self).__init__()
        self.tempo = tempo
        self.rhythm_profile = rhythm_profile
        self.grid = len(self.rhythm_profile)
        self.durations = []
        self.last_beat = None
        self.last_quantized_tick = None
        self.last_real_tick = None

        self.tempo_map  = SimpleTempoMap(self.tempo)
        self.sched = AudioScheduler(self.tempo_map)

    # starts detecting the rhythm starting at this instant
    def start(self):
        now = self.sched.get_tick()
        self.last_real_tick = now
        snap = self.snap_note_to_grid(now)
        self.last_quantized_tick = snap
        self.last_beat = quantize_tick_down(now, kTicksPerQuarter)

    # detects the duration of the note ending at this instant
    def add_note(self):
        if not self.last_beat:
            self.start()
        else:
            now = self.sched.get_tick()
            note = now - self.last_quantized_tick
            duration = self.snap_note_to_grid(note)
            self.last_beat += duration/kTicksPerQuarter
            self.last_real_tick = now
            self.last_quantized_tick += duration
            self.durations.append(duration)
        print self.durations

    # takes in a tick, and snaps the tick to a recognizable beat
    # according to rhythm_profile
    def snap_note_to_grid(self, tick):
        print tick
        beats = int(tick/kTicksPerQuarter)
        tick = tick - beats*kTicksPerQuarter
        tick = float(tick*self.grid)/float(kTicksPerQuarter)
        print tick
        snap = bisect_left(self.rhythm_profile, tick)
        return beats*kTicksPerQuarter + snap*kTicksPerQuarter/self.grid


class PitchSnap(object):
    def __init__(self):
        super(PitchSnap, self).__init__()
        self.started = False
        self.pitches = []
        self.rel_pitches = []
        self.abs_pitches = []
        self.low_pitch = 40
        self.high_pitch = 77
        self.last_pitch = 0

    def start(self):
        self.pitches = []
        self.started = True

    def snap_pitch(self):
        if not self.started:
            self.start()
        self.pitches = np.array(self.pitches)
        self.pitches = [a for a in self.pitches if a > self.low_pitch and a < self.high_pitch]
        if len(self.pitches) > 0:
            avg = np.percentile(self.pitches, 50)

            abs_pitch = round(avg)
            abs_array = [a for a in self.pitches if a >= abs_pitch - .5 and a <= abs_pitch + .5]
            abs_confidence = float(len(abs_array))/float(len(self.pitches))
            self.abs_pitches.append((abs_pitch, abs_confidence))

            rel_pitch = round(avg - self.last_pitch)
            rel_array = [a for a in self.pitches if a >= rel_pitch - .5 and a <= rel_pitch + .5]
            rel_confidence = float(len(rel_array))/float(len(self.pitches))
            self.rel_pitches.append((rel_pitch, rel_confidence))

            self.last_pitch = avg
            print self.abs_pitches
            print self.rel_pitches
        self.pitches = []


    def on_update(self, pitch):
        self.pitches.append(pitch)



class MainWidget1(BaseWidget) :
    def __init__(self):
        super(MainWidget1, self).__init__()

        self.audio = Audio(NUM_CHANNELS, input_func=self.receive_audio)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)
        self.io_buffer = IOBuffer()
        self.mixer.add(self.io_buffer)
        self.pitch = PitchDetector()

        self.recording = False
        self.monitor = False
        self.channel_select = 0
        self.input_buffers = []
        self.live_wave = None
        self.song_snips = []

        # separate audio channel for the metronome
        self.metro_audio = Audio(NUM_CHANNELS)
        self.synth = Synth('../../data/FluidR3_GM.sf2', Audio.sample_rate)

        self.tempo = 50
        self.rhythm_detector = RhythmDetector(self.tempo, rel_rhythm)
        # take TempoMap, AudioScheduler from RhythmDetector
        self.tempo_map  = self.rhythm_detector.tempo_map
        self.sched = self.rhythm_detector.sched

        # connect scheduler into audio system
        self.metro_audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)

        # create the metronome:
        self.metro = Metronome(self.sched, self.synth)

        self.pitch_snap = PitchSnap()

        # used for playback
        self.song = []
        self.note_song = NoteSong(TimeSig(4,4), self.tempo)

        self.seq = NoteSequencer(self.sched, self.synth, 1, (0, 0), self.song, False, self.add_snips)

        self.info = topleft_label()
        self.add_widget(self.info)

        self.anim_group = AnimGroup()

        self.canvas.add(self.anim_group)

    def on_update(self) :
        self.audio.on_update()
        self.metro_audio.on_update()
        self.anim_group.on_update()

        self.info.text = 'fps:%d\n' % kivyClock.get_fps()
        self.info.text += 'load:%.2f\n' % self.audio.get_cpu_load()
        self.info.text += 'gain:%.2f\n' % self.mixer.get_gain()
        self.info.text += "pitch: %.1f\n" % self.cur_pitch

        self.info.text += "c: analyzing channel:%d\n" % self.channel_select
        self.info.text += "r: toggle recording: %s\n" % ("OFF", "ON")[self.recording]
        self.info.text += "m: monitor: %s\n" % ("OFF", "ON")[self.monitor]
        self.info.text += "p: playback memory buffer"

    def receive_audio(self, frames, num_channels) :
        # handle 1 or 2 channel input.
        # if input is stereo, mono will pick left or right channel. This is used
        # for input processing that must receive only one channel of audio (RMS, pitch, onset)
        if num_channels == 2:
            mono = frames[self.channel_select::2] # pick left or right channel
        else:
            mono = frames

        # pitch detection: get pitch and display on meter and graph
        self.cur_pitch = self.pitch.write(mono)
        self.pitch_snap.on_update(self.cur_pitch)
        if self.recording:
            self.input_buffers.append(frames)

    def add_snips(self, idx):
        # this is kind of hack-y so should eventually be fixed
        self.mixer.add(WaveGenerator(self.song_snips[idx+1], loop=True))

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'c' and NUM_CHANNELS == 2:
            self.channel_select = 1 - self.channel_select

        # turn metronome on/
        if keycode[1] == '1':
            self.metro.toggle()

        # turn sequencer on/off
        if keycode[1] == '2':
            self.seq.toggle()

        if keycode[1] == 'x':
            self.recording = True
            self._process_input()
            self.rhythm_detector.add_note()
            self.pitch_snap.snap_pitch()
            if len(self.rhythm_detector.durations) > 0:
                duration = self.rhythm_detector.durations[-1]
                abs_pitch = self.pitch_snap.abs_pitches[-1]
                rel_pitch = self.pitch_snap.rel_pitches[-1]
                pitch_obj = Pitch(abs_pitch[0], abs_pitch[1], rel_pitch[0], rel_pitch[1])
                pitch = pitch_obj.get_best_guess()
                noteinfo = NoteInfo(pitch_obj, duration)
                self.note_song.add_to_solo_voice(note_info)
                self.song.append((int(duration), int(pitch)))


        # adjust mixer gain
        gf = lookup(keycode[1], ('up', 'down'), (1.1, 1/1.1))
        if gf:
            new_gain = self.mixer.get_gain() * gf
            self.mixer.set_gain( new_gain )

        # adjust tempo gain
        # TODO: this currently doesn't work
        tempo_ctrl = lookup(keycode[1], ('left', 'right'), (-1, 1))
        if tempo_ctrl:
            self.tempo += tempo_ctrl
            self.rhythm_detector = RhythmDetector(self.tempo, self.rhythm_detector.rhythm_profile)

    def _process_input(self) :
        data = combine_buffers(self.input_buffers)
        print 'live buffer size:', len(data) / NUM_CHANNELS, 'frames'
        write_wave_file(data, NUM_CHANNELS, 'recording.wav')
        self.song_snips.append(WaveArray(data, NUM_CHANNELS))
        self.input_buffers = []

# pass in which MainWidget to run as a command-line arg
run(MainWidget1)
