import sys
sys.path.append('..')

from common.clock import *
from common.constants import *
from math import *
from noteclass import *

from bisect import bisect_left
import numpy as np


#Maybe use to give rhythm confidence?
#rel_rhythm = [2.5, 2.5, 2.5, 3.7, 4.5, 4.5, 7.7, 7.7, 8.3, 9.5, 9.5, 9.5]
#beat_rhythm = [2.5, 2.5, 2.5, 3.7, 4.5, 4.5, 7.7, 7.7, 8.5, 9.7, 9.7, 9.7]

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

    def set_tempo(self, tempo):
        self.tempo = tempo
        self.tempo_map = SimpleTempoMap(self.tempo)
        self.sched = AudioScheduler(self.tempo_map)

    # takes in a tick, and snaps the tick to a recognizable beat
    # according to rhythm_profile
    def snap_note_to_grid(self, tick):
        beats = int(tick/kTicksPerQuarter)
        tick = tick - beats*kTicksPerQuarter
        tick = float(tick*self.grid)/float(kTicksPerQuarter)
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
        pre_len = len(self.pitches)
        self.pitches = [a for a in self.pitches if a > self.low_pitch and a < self.high_pitch]
        if pre_len > 0 and len(self.pitches)/float(pre_len) < .5:
            abs_pitch = 0
            abs_confidence = len(self.pitches)/float(pre_len)
            self.abs_pitches.append((abs_pitch, abs_confidence))
            rel_pitch = -1*round(self.last_pitch)
            rel_confidence = len(self.pitches)/float(pre_len)
            self.rel_pitches.append((rel_pitch, rel_confidence))
            self.last_pitch = 0
        elif len(self.pitches) > 0:

            avg = np.percentile(self.pitches, 50)

            abs_pitch = round(avg)
            abs_array = [a for a in self.pitches if a >= abs_pitch - .5 and a <= abs_pitch + .5]
            abs_confidence = float(len(abs_array))/float(len(self.pitches))
            self.abs_pitches.append((abs_pitch, abs_confidence))

            rel_pitch = round(avg - self.last_pitch)
            rel_array = [a for a in self.pitches if a - self.last_pitch >= rel_pitch - .5 and a - self.last_pitch <= rel_pitch + .5]
            #rel_confidence = 0
            rel_confidence = float(len(rel_array))/float(len(self.pitches))
            self.rel_pitches.append((rel_pitch, rel_confidence))

            self.last_pitch = avg
        self.pitches = []


    def on_update(self, pitch):
        self.pitches.append(pitch)


def transpose_song(song):
    """
    If the notes in self.song cannot render in the treble clef, moves the bottom note of the sequence to middle C.
    """
    pitches = [note[1] for note in song]
    min_pitch = 60
    for pitch in pitches:
        if pitch !=0 and pitch < min_pitch:
            min_pitch = pitch
    if min_pitch < MIN_TREBLE_PITCH:
        for i in range(len(song)):
            current = song[i]
            if current[1] != 0:
                song[i] = (current[0], MIN_TREBLE_PITCH + (current[1] - min_pitch))

    return song

def trim_notes_for_playback(notes):
    i = len(notes)
    while i >= 0:
        i -= 1
        if notes[i][1] >= MIN_TREBLE_PITCH:
            break
    return notes[0:i+1]

def trim_to_measures(notes, measure_length, num_measures):
    ret = []
    rest = notes[:]
    max_length = measure_length*num_measures
    ret_length = 0
    for note in notes:
        if ret_length >= max_length:
            return ret, rest
        elif ret_length + note[0] > max_length:
            new_note = [max_length - ret_length, note[1]]
            ret_length = max_length
            rest[0] = [note[0] - (max_length - ret_length), note[1]]
            ret.append(new_note)
        else:
            rest.pop(0)
            ret.append(note)
            ret_length += note[0]
    padding = measure_length*num_measures - ret_length
    if padding > 0:
        ret.append([padding, 0])
    return ret, rest


