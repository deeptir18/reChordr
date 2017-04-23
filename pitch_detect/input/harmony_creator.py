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

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate

from random import randint
import aubio
from bisect import bisect_left
import numpy as np

NUM_CHANNELS = 2


maj_scale = {0: 2, 2: 1, 4: 1, 5: 1, 7: 1, 9: 1, 11: 1}
harm_min_scale = {0: 2, 2: 1, 3: 1, 5: 1, 7: 1, 9: 1, 10: 1}

four_chords = ((1, [0, 4, 7]), (4, [5, 9, 0]), (5, [7, 11, 2]), (6, [9, 0, 4]))
# accepts song as an array of tuples (duration, pitch)
# key is (semitones above C, is major)
class HarmonyCreator(object):
    def __init__(self, song, key=None):
        super(HarmonyCreator, self).__init__()
        self.song = song
        if key:
            self.key = key
        else:
            self.key = self.detect_key()

    def detect_key(self):
        major = []
        minor = []
        for i in range(12):
            maj_key = 0
            min_key = 0
            for note in self.song:
                if note[1] > 0:
                    pitch_class = (note[1] - i) % 12
                    if pitch_class in maj_scale.keys():
                        maj_key += maj_scale[pitch_class]*note[0]/float(kTicksPerQuarter)
                    if pitch_class in harm_min_scale.keys():
                        min_key += harm_min_scale[pitch_class]*note[0]/float(kTicksPerQuarter)

            major.append(maj_key)
            minor.append(min_key)
        if max(major) >= max(minor):
            return (major.index(max(major)), True)
        else:
            return (minor.index(max(minor)), False)

    # measure_length given in ticks
    def get_measures(self, measure_length):
        measures = []
        current_measure = []
        # measured in ticks
        current_length = 0
        for note in self.song:
            if current_length + note[0] <= measure_length:
                current_measure.append(note)
                current_length += note[0]
            elif current_length == measure_length:
                measures.append(current_measure)
                current_measure = [note]
                current_length = 0
            else:
                dur = measure_length - current_length
                current_measure.append((dur, note[1]))
                measures.append(current_measure)
                current_measure = [(note[0] - dur, note[1])]
                current_length = note[0] - dur
        if current_length > 0:
            current_measure.append((measure_length - current_length, 0))
            measures.append(current_measure)
        return measures

    def get_harmonies(self, measures):
        chords = []
        for m in measures:
            chord_weights = []
            for chord in four_chords:
                weight = 0
                for note in m:
                    if note[1] > 0:
                        print 'hello'
                        pitch_class = note[1] - self.key[0]
                        if pitch_class in chord[1]:
                            print 'hi'
                            weight += float(note[0])/float(kTicksPerQuarter)
                chord_weights.append(weight)
            print chord_weights
            best_chord = max(chord_weights)
            potential_chords = [i for i, x in enumerate(chord_weights) if x == best_chord]
            print potential_chords
            chords.append(potential_chords)
        return chords



kSomewhere = ((960, 60), (960, 72), (480, 71), (240, 67), (240, 69), (480, 71), (480, 72), )
AllMyLoving = ((480*2, 0), (480, 69), (240, 68), (480*2, 66), (240, 0), (240, 68), (480, 69), (480, 71), (720, 73))
x = HarmonyCreator(AllMyLoving)
print x.get_measures(480*4)
print x.get_harmonies(x.get_measures(480*4))