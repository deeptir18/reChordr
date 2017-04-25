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

major = 'MAJOR'
harm_minor = 'HARMONIC_MINOR'
nat_minor = 'NATURAL_MINOR'

voice_map ={"SOPRANO": 0, "ALTO": 1, "TENOR": 2, "BASS": 3}
scales={"MAJOR": (0, 2, 4, 5, 7, 9, 11), "HARMONIC_MINOR": (0, 2, 3, 5, 7, 8, 11), "NATURAL_MINOR": (0, 2, 3, 5, 7, 8, 10)}

# takes in int representing midi pitch
class PitchClass(object):
    def __init__(self, midi):
        super(PitchClass)
        self.pitch_class = midi % 12

    def contains(self, midi):
        return (midi % 12 == self.pitch_class)

    def get_notes_in_range(self, pitch_range):
        # given a frequency f, find all the octaves of f that are in range [low, hi]
        ret = range(pitch_range[0], pitch_range[1])
        ret = [i for i in ret if self.contains(i)]
        return ret


    def __str__(self):
        names = ['C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B']
        return names[self.pitch_class]

# pitch is midi, scale_type is either major, harmonic minor, natural minor
class Key(object):
    def __init__(self, pitch, scale_type):
        super(Key, self).__init__()
        self.pitch = pitch
        self.scale_type = scale_type
        if scale_type == major:
            self.scale = scales[major]
        elif scale_type == harm_minor:
            self.scale = scales[harm_minor]
        else:
            self.scale = scales[nat_minor]

    def contains(self, midi):
        return self.get_scale_degree(midi) > 0

    def get_consonance(self, notes, coeffs=[2., 1., 1., 1., 1., 1., 1.]):
        consonance = 0
        for note in notes:
            if note[1] > 0:
                x = self.get_scale_degree(note[1])
                if x > 0:
                    consonance += float(coeffs[x - 1]*note[0])/float(kTicksPerQuarter)
        return consonance

    def get_scale_degree(self, midi):
        for x in self.scale:
            if PitchClass(x + self.pitch).contains(midi):
                return self.scale.index(x) + 1
        return -1

# scale_degrees is a tuple
class Chord(object):
    def __init__(self, scale_degrees):
        super(Chord, self).__init__()
        self.scale_degrees = scale_degrees

    def contains(self, midi, key):
        return (key.get_scale_degree(midi) in self.scale_degrees)

    def get_chord_in_key(self, key):
        pitches = []
        for i in range(12):
            if self.contains(i, key):
                pitches.append(PitchClass(i))
        return pitches

    def get_consonance(self, measure, key, coeffs=None):
        if not coeffs:
            coeffs = [1.]*len(self.scale_degrees)
        consonance = 0
        total = 0
        for note in measure:
            if note[1] > 0:
                total += note[0]
                x = key.get_scale_degree(note[1])
                if x in self.scale_degrees:
                    idx = self.scale_degrees.index(x)
                    consonance += coeffs[idx]*note[0]
        if total == 0:
            return 0
        return float(consonance)/float(total)

    def __str__(self):
        return str(self.scale_degrees)


one_chord = Chord((1, 3, 5))
four_chord = Chord((4, 6, 1))
five_chord = Chord((5, 7, 2))
six_chord = Chord((6, 1, 3))
three_chord = Chord((3, 5, 7))
two_chord = Chord((2, 4, 6))
seven_chord = Chord((7, 2, 4))

maj_chords = set([one_chord, two_chord, three_chord, four_chord,
              five_chord, six_chord, seven_chord])

maj_edges = {three_chord: set([three_chord, six_chord]),
             six_chord: set([two_chord, four_chord, six_chord]),
             two_chord: set([two_chord, five_chord, seven_chord]),
             four_chord: set([four_chord, five_chord, seven_chord]),
             five_chord: set([one_chord, five_chord]),
             seven_chord: set([one_chord, three_chord, seven_chord]),
             one_chord: set([one_chord, two_chord, three_chord, four_chord,
                            five_chord, six_chord, seven_chord])}



# accepts song as an array of tuples (duration, pitch)
# measure_length is the length of the measure in ticks
# key is a Key object
class ChordPredictor(object):
    def __init__(self, song, measure_length, key=None):
        super(ChordPredictor, self).__init__()
        self.song = song
        if key:
            self.key = key
        else:
            self.key = self._detect_key()
        self.measures = self._get_measures(measure_length)

    def _detect_key(self):
        major_fit = []
        harm_minor_fit = []
        for i in range(12):
            maj_scale = Key(i, major)
            harm_min_scale = Key(i, harm_minor)
            major_fit.append(maj_scale.get_consonance(self.song))
            harm_minor_fit.append(harm_min_scale.get_consonance(self.song))
        if max(major_fit) >= max(harm_minor_fit):
            key = major_fit.index(max(major_fit))
            return Key(key, major)
        else:
            key = harm_minor_fit.index(max(harm_minor_fit))
            return Key(key, harm_minor)

    # measure_length given in ticks
    def _get_measures(self, measure_length):
        measures = []
        current_measure = []
        # measured in ticks
        current_length = 0
        for note in self.song:
            # if note fits in measure, add it
            if current_length + note[0] <= measure_length:
                current_measure.append(note)
                current_length += note[0]
            # elif measure is full, start a new one
            elif current_length == measure_length:
                measures.append(current_measure)
                current_measure = [note]
                current_length = note[0]
            # else, split the note over the measure
            else:
                dur = measure_length - current_length
                current_measure.append((dur, note[1]))
                measures.append(current_measure)
                current_measure = [(note[0] - dur, note[1])]
                current_length = note[0] - dur
        # pad the rest of the measure with a rest
        if current_length > 0:
            # this is a little sloppy
            current_measure.append((measure_length - current_length, 0))
            measures.append(current_measure)
        return measures

    def get_all_next_chords(self, idx, prev_chord=None):
        if idx >= len(self.measures) or idx < 0:
            return []
        measure = self.measures[idx]
        if prev_chord and self.key.scale_type == major:
            potential_chords = maj_edges[prev_chord]
        else:
            potential_chords = maj_chords
        chord_weights = {}
        for chord in potential_chords:
            chord_weights[chord] = chord.get_consonance(measure, self.key)
        max_val = min(.5, max(chord_weights.values()))
        chords = [key for key in chord_weights.keys() if chord_weights[key] >= max_val]
        return chords

    def get_one_next_chord(self, idx, prev_chord=None):
        chords = self.get_all_next_chords(idx, prev_chord)
        return chords[0]

    def get_one_option(self):
        chords = []
        for i in range(len(self.measures)):
            if i > 0:
                chords.append(self.get_one_next_chord(i, chords[i-1]))
            else:
                chords.append(self.get_one_next_chord(i))
        return chords


class VoicePredictor(object):
    def __init__(self, chord, key, prev_voicing=None):
        super(VoicePredictor, self).__init__()
        self.chord = chord
        self.key = key
        # chord pitches: a list of the PitchClass objects in chord in key
        self.chord_pitches = self.chord.get_chord_in_key(self.key)
        self.prev_voicing = prev_voicing

    def get_pitches_in_range(self, voice):
        # got info from https://musescore.org/en/node/4581
        # voice_part -> one of soprano, alto, tenor, base
        
        if voice == soprano:
            voice_range = [36, 60]
        elif voice == alto:
            voice_range = [29,53]
        elif voice == tenor:
            voice_range = [24, 48]
        else:
            voice_range = [15,51]
        pitch_options = {}
        for pitch in self.chord_pitches:
            pitch_options[pitch] = pitch.get_notes_in_range(voice_range)
        return pitch_options

    def chord_voicing_options(self):
        # returns a list of possible chord voicings for this chord
        pitch_choices = {}
        for voice in [soprano, alto, tenor, bass]:
            options = self.get_pitches_in_range(voice)
            pitch_choices[voice] = options

        # what are all possible ways to assign this chord?
        perms =  list(itertools.product(self.chord_pitches, repeat=4))
        final_list = []
        for perm in perms: # ways to assign root, third, fifth, to SATB
            if self.chord_pitches[0] in perm and self.chord_pitches[1] in perm and self.chord_pitches[2] in perm:
                # count if third was doubled => Don't allow this!
                count = 0
                for pitch in perm:
                    if pitch == self.chord_pitches[1]:
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
                voicing = ChordVoicing(*possibility)
                if voicing.is_acceptable_voicing():
                    voicings.append(voicing)

        return voicings

    def get_initial_voicing(self):
        # NOTE: here, for right now, just takes the first options
        # We might want to come up with a smart way to get them
        options = self.chord_voicing_options()
        return options[0]

    def get_best_voicing(self, voicings=None):
        # given a previous voicing, generate the best possible voicing
        if not voicings:
            voicings = self.chord_voicing_options()
        distance_map= {}
        for voicing in voicings:
            dist = self.prev_voicing.distance(voicing)
            if dist not in distance_map:
                distance_map[dist] = [voicing]
            else:
                distance_map[dist].append(voicing)

        distances = distance_map.keys()
        distances.sort()
        best_voicings = distance_map[distances[0]]
        for voicing in best_voicings:
            print voicing
        ind = randint(0, len(best_voicings) - 1)
        return best_voicings[ind]



class ChordVoicing(object):
    def __init__(self, soprano, alto, tenor, bass):
        super(ChordVoicing, self).__init__()
        self.soprano = soprano
        self.alto = alto
        self.tenor = tenor
        self.bass = bass

    def distance(self, other):
        #### NOTE: the distance metric can change based on what metric we want to use for an optional way to change voices
        return abs(other.soprano - self.soprano) + abs(other.alto - self.alto) + abs(other.tenor - self.tenor) + abs(other.bass - self.bass)

    def is_acceptable_voicing(self):
        # only voices adjacent to each other can cross\
        if self.soprano <= self.tenor or self.soprano <= self.bass:
            return False

        if self.alto <= self.bass:
            return False

        # maybe I'm missing something, but is the first clause even necessary?
        if self.soprano < self.alto and (self.alto - self.soprano >=2 ):
            return False
        if self.alto < self.tenor and (self.tenor - self.alto >=2 ):
            return False
        if self.tenor < self.bass and (self.bass - self.tenor >=2 ):
            return False
        return True

    def __str__(self):
        return "SOPRANO: {}, ALTO: {}, TENOR: {}, BASS: {}".format(self.soprano, self.alto, self.tenor, self.bass)





a_maj = Key(57, major)

v = VoicePredictor(one_chord, a_maj, ChordVoicing(52, 45, 36, 23))
print v.get_best_voicing()


kSomewhere = ((960, 60), (960, 72), (480, 71), (240, 67), (240, 69), (480, 71), (480, 72), )
allMyLoving = ((480*2, 0), (480, 69), (240, 68), (480*2, 66), (240, 0), (240, 68), (480, 69), (480, 71), (720, 73))
riversAndRoads = ((480, 0), (240, 55), (480, 60), (240, 62), (480, 64), (240, 67),
                  (480, 69), (240, 67), (360, 64), (120, 64), (240, 67),
                  (480, 69), (240, 69), (480, 67), (240, 60), (240, 64), (480*3+240, 0))
c_maj = Key(60, major)
x = ChordPredictor(riversAndRoads, 480*1.5, c_maj)

chords = x.get_one_option()
for chord in chords:
    print chord

