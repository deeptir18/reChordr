import sys
import itertools
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


from random import randint
import aubio
from bisect import bisect_left
import numpy as np

NUM_CHANNELS = 2
soprano = 'SOPRANO'
alto = 'ALTO'
tenor = 'TENOR'
bass = 'BASS'

voice_map ={"SOPRANO": 0, "ALTO": 1, "TENOR": 2, "BASS": 3}

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
                        pitch_class = (note[1] - self.key[0]) % 12
                        if pitch_class in chord[1]:
                            weight += float(note[0])/float(kTicksPerQuarter)
                chord_weights.append(weight)
            print chord_weights
            best_chord = max(chord_weights)
            potential_chords = [i for i, x in enumerate(chord_weights) if x == best_chord]
            print potential_chords
            chords.append(potential_chords)
        return chords


class PitchClass(object):
    def __init__(self, semitones_from_C):
        super(PitchClass)
        self.pitch_class = semitones_from_C % 12

    def contains(self, midi):
        return (midi % 12 == self.pitch_class)

    def to_string(self):
        names = ['C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B']
        return names[self.pitch_class]


class Scale(object):
    def __init__(self, key, is_major, is_harmonic=True):
        super(Scale, self).__init__()
        self.key = key
        if is_major:
            self.scale = [0, 2, 4, 5, 7, 9, 11]
        elif is_harmonic:
            self.scale = [0, 2, 3, 5, 7, 8, 11]
        else:
            self.scale = [0, 2, 3, 5, 7, 8, 10]

    def contains(self, midi):
        for x in self.scale:
            if PitchClass(x + self.key.pitch_class).contains(midi):
                return True
        return False

    def get_pitch_class(self, scale_degree):
        return PitchClass(self.scale[scale_degree - 1] + self.key.pitch_class)

    def get_scale_degree(self, midi):
        for x in self.scale:
            if PitchClass(x + self.key.pitch_class).contains(midi):
                return self.scale.index(x) + 1
        return -1


def get_pitches_in_range(voice, chord_pitches):
    # got info from https://musescore.org/en/node/4581
    # voice -> one of soprano, alto, tenor, base
    # chord pitches -> a list of the pitches in the chord
    if voice == soprano:
        voice_range = [36, 60]
    elif voice == alto:
        voice_range = [29,53]
    elif voice == tenor:
        voice_range = [24, 48]
    else:
        voice_range = [15,51]
    pitch_options = {}
    for pitch in chord_pitches:
        pitch_options[pitch] = get_note_in_range(pitch, voice_range)
    return pitch_options


def get_note_in_range(f, range):
    # given a frequency f, find all the octaves of f that are in range [low, hi]
    ret = []
    if f < range[0]:
        cur_freq = f
        while cur_freq <= range[1]:
            cur_freq += 12
            if cur_freq >= range[0] and cur_freq <= range[1]:
                ret.append(cur_freq)
    elif f > range[1]:
        cur_freq = f
        while cur_freq >= range[0]:
            cur_freq -= 12
            if cur_freq >= range[0] and cur_freq <= range[1]:
                ret.append(cur_freq)
    else:
        assert (f>=range[0] and f <=range[1])
        ret.append(f)
        cur_freq = f
        while cur_freq >= range[0]:
            cur_freq -= 12
            if cur_freq >= range[0] and cur_freq <= range[1]:
                ret.append(cur_freq)

        cur_freq = f
        while cur_freq <= range[1]:
            cur_freq += 12
            if cur_freq >= range[0] and cur_freq <= range[1]:
                ret.append(cur_freq)

    return ret

def is_acceptable_voicing(voice):
    # only voices adjacent to each other can cross\
    if voice[0] <= voice[2] or voice[0] <= voice[3]:
        return False

    if voice[1] <= voice[3]:
        return False

    for i in range(3):
        if voice[i] < voice[i+1] and (voice[i+1] - voice[i] >=2 ):
            return False
    return True

def get_initial_voicing(chord, key):
    # NOTE: here, for right now, just takes the first options
    # We might want to come up with a smart way to get them
    options = chord_voicing_options(chord, key)
    return options[0]

def chord_voicing_options(chord, key):
    # returns a list of possible chord voicings for this chord
    pitch_choices = {}
    chord_pitches = chord.get_chord_in_key(key)
    for voice in [soprano, alto, tenor, bass]:
        options = get_pitches_in_range(voice, chord_pitches)
        pitch_choices[voice] = options

    # what are all possible ways to assign this chord?
    perms =  list(itertools.product(chord_pitches, repeat=4))
    final_list = []
    for perm in perms: # ways to assign root, third, fifth, to SATB
        if chord_pitches[0] in perm and chord_pitches[1] in perm and chord_pitches[2] in perm:
            # count if third was doubled => Don't allow this!
            count = 0
            for pitch in perm:
                if pitch == chord_pitches[1]:
                    count += 1
            if count == 1:
                final_list.append(perm)

    voicings = []
    for perm in final_list:
        # figure out specific frequencies that go to each voice
        add = []
        for voice in [soprano, alto, tenor, bass]:
            index = voice_map[voice]
            add.append(pitch_choices[voice][perm[index]])
        for possibility in list(itertools.product(*add)):
            if is_acceptable_voicing(possibility):
                voicings.append(ChordVoicing(*possibility))

    return voicings

def get_best_voicing(voicings, prev_voicing):
    # given a previous voicing, generate the best possible voicing
    distance_map= {}
    for voicing in voicings:
        dist = prev_voicing.distance(voicing)
        if dist not in distance_map:
            distance_map[dist] = [voicing]
        else:
            distance_map[dist].append(voicing)

    distances = distance_map.keys()
    distances.sort()
    best_voicings = distance_map[distances[0]]
    for voicing in best_voicings:
        print voicing
    ind = randint(0, len(best_voicings))
    return best_voicings[ind]


class ChordVoicing(object):
    def __init__(self, soprano, alto, tenor, bass):
        self.soprano = soprano
        self.alto = alto
        self.tenor = tenor
        self.bass = bass

    def distance(self, other):
        #### NOTE: the distance metric can change based on what metric we want to use for an optional way to change voices
        return abs(other.soprano - self.soprano) + abs(other.alto - self.alto) + abs(other.tenor - self.tenor) + abs(other.bass - self.bass)

    def __str__(self):
        return "SOPRANO: {}, ALTO: {}, TENOR: {}, BASS: {}".format(self.soprano, self.alto, self.tenor, self.bass)


class Chord(object):
    def __init__(self, scale_degrees, is_major, is_harmonic=True):
        super(Chord, self).__init__()
        self.scale_degrees = scale_degrees
        self.is_major = is_major
        self.is_harmonic = is_harmonic

    def contains(self, midi, key):
        scale = Scale(key, self.is_major, self.is_harmonic)
        return (scale.get_scale_degree(midi) in self.scale_degrees)


    def get_chord_in_key(self, key):
        return [(key + deg - 1) for deg in self.scale_degrees] # in order of root, third, fifth, etc.


one_chord = Chord([1, 3, 5], True)
four_chord = Chord([4, 6, 1], True)
five_chord = Chord([5, 7, 2], True)
six_chord = Chord([6, 1, 3], True)
three_chord = Chord([3, 5, 7], True)


get_best_voicing(chord_voicing_options(one_chord, 57), ChordVoicing(52, 45, 36, 23))









# parts is of the form [(lowest pitch, highest pitch), etc.]
# def get_all_part_options(parts, chord):
#     pass



# def get_all_valid_notes(part, chord):
#     valid = []
#     for note in chord:
#         while note <= part[1]:
#             if note >= part[0]:
#                 valid.append(note)
#             note += 12
#     valid.sort()
#     return valid




# kSomewhere = ((960, 60), (960, 72), (480, 71), (240, 67), (240, 69), (480, 71), (480, 72), )
# AllMyLoving = ((480*2, 0), (480, 69), (240, 68), (480*2, 66), (240, 0), (240, 68), (480, 69), (480, 71), (720, 73))
# x = HarmonyCreator(AllMyLoving)
# print x.get_measures(480*4)
# print x.get_harmonies(x.get_measures(480*4))

# print get_all_valid_notes((60, 79), [0, 4, 7])
