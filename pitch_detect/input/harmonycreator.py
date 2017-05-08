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


from random import randint, random
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
chord_types={"MAJOR": (0, 4, 7), "MINOR": (0, 3, 7), "DIM": (0, 3, 6), "AUG": (0, 4, 8), "SUS4": (0, 5, 7)}

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

# semitones_above_key is an int corresponding to the bass note
# chord_type is MAJOR, MINOR, DIM, AUG, or SUS4
class Chord(object):
    def __init__(self, semitones_above_key, chord_type):
        super(Chord, self).__init__()
        self.semitones_above_key = semitones_above_key
        if chord_type in chord_types:
            self.chord_pitches = chord_types[chord_type]
        else:
            self.chord_pitches = []

    def contains(self, midi, key):
        for x in self.chord_pitches:
            if PitchClass(key.pitch + self.semitones_above_key + x).contains(midi):
                return True
        return False

    def get_chord_in_key(self, key):
        pitches = []
        for i in range(12):
            if self.contains(i, key):
                pitches.append(PitchClass(i))
        return pitches

    def get_consonance(self, measure, key):
        consonance = 0
        total = 0
        for note in measure:
            if note[1] > 0:
                total += note[0]
                if self.contains(note[1], key):
                    consonance += note[0]
        if total == 0:
            return 0
        return float(consonance)/float(total)

    def __str__(self):
        ret = ''
        for x in self.get_chord_in_key(Key(60, "MAJOR")):
            ret += str(x) + ' '
        return ret

    def __eq__(self, other):
        return str(self) == str(other)

mat_chords = []
for i in range(12):
    mat_chords.append(Chord(i, "MAJOR"))
    mat_chords.append(Chord(i, "MINOR"))
    mat_chords.append(Chord(i, "DIM"))
    mat_chords.append(Chord(i, "AUG"))
    mat_chords.append(Chord(i, "SUS4"))

def read_matrix(filepath):
    start = []
    transition = []
    end = []
    file = open(filepath)
    lines = file.readlines()
    start_len = int(lines.pop(0))
    for i in range(start_len):
        start.append(float(lines.pop(0)))
    start = np.array(start)
    dims = lines.pop(0).split(' ')
    dims[0] = int(dims[0])
    dims[1] = int(dims[1])
    for i in range(dims[1]):
        row = []
        for j in range(dims[0]):
            row.append(float(lines.pop(0)))
        transition.append(np.array(row))
    transition = np.array(transition)
    end_len = int(lines.pop(0))
    for i in range(end_len):
        end.append(float(lines.pop(0)))
    end = np.array(end)
    return start, transition, end


matrix = read_matrix('../data/pop.txt')



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

    def get_possible_chords(self, idx):
        if idx >= len(self.measures) or idx < 0:
            return []
        measure = self.measures[idx]
        chord_weights = []
        for chord in mat_chords:
            chord_weights.append(chord.get_consonance(measure, self.key))
        max_val = max(chord_weights)
        chords = [1 if val >= max_val else 0 for val in chord_weights]
        return chords

    def get_top_three(self, idx):
        chords = self.get_possible_chords(idx)
        top_three = []
        while len(top_three) < 3:
            i = randint(0, len(chords) - 1)
            if chords[i] == 1:
                top_three.append(mat_chords[i])
        return top_three


    def get_one_chord(self, idx, prev_chord=None):
        chords = self.get_possible_chords(idx)
        row = []
        if not prev_chord:
            row = matrix[0]
        else:
            row = matrix[1][mat_chords.index(prev_chord)]

        rand = random()
        row = row*np.array(chords)
        
        index = np.argmax(abs(row))
        return mat_chords[index]

    def get_all_chords(self):
        chords = [self.get_one_chord(0)]
        for i in range(len(self.measures)):
            chords.append(self.get_one_chord(i, chords[i-1]))
        return chords

    def get_all_possible_chord_progs(self):
        chords = []
        for i in range(len(self.measures)):
            chords.append(self.get_top_three(i))
        return list(itertools.product(*chords))

    def get_best_chord_prog(self, chord_progs, matrix):
        for chords in chord_progs:
            print "hello"
            for chord in chords:
                print chord
        print len(chord_progs)
        fits = []
        fit = 0
        for chords in chord_progs:
            fit = matrix[0][mat_chords.index(chords[0])]
            for i in range(1, len(chords)):
                fit += matrix[1][mat_chords.index(chords[i-1])][mat_chords.index(chords[i])]
            fit += matrix[2][mat_chords.index(chords[-1])]
            fits.append(fit)
        fits_original = fits[:]
        fits.sort(reverse=True)
        print fits
        print fits_original
        best_chords = [chord_progs[fits_original.index(fits[0])], chord_progs[fits_original.index(fits[1])],
                       chord_progs[fits_original.index(fits[2])], chord_progs[fits_original.index(fits[3])]]

        return best_chords


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
            voice_range = [65, 72]
        elif voice == alto:
            voice_range = [55,65]
        elif voice == tenor:
            voice_range = [48, 53]
        else:
            voice_range = [43,55]
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
        best_voicings = distance_map[distances[0]]
        highest = 0
        best = None
        for voicing in best_voicings:
            if voicing.sum() > highest:
                highest = voicing.sum()
                best = voicing
        ind = randint(0, len(best_voicings) - 1)
        if best != None:
            return best
        else:
            return best_voicings[ind]



class ChordVoicing(object):
    def __init__(self, soprano, alto, tenor, bass):
        super(ChordVoicing, self).__init__()
        self.soprano = soprano
        self.alto = alto
        self.tenor = tenor
        self.bass = bass

    def sum(self):
        return self.soprano + self.alto + self.tenor + self.bass

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


def create_note_sequencers(voicings, length):
    sop = ()
    alt = ()
    ten = ()
    bas = ()

    for voicing in voicings:
        sop += ((length, voicing.soprano),)
        alt += ((length, voicing.alto),)
        ten += ((length, voicing.tenor),)
        bas += ((length, voicing.bass),)

    return {soprano: sop, alto: alt, tenor: ten, bass: bas}

somewhere = [(600, 60), (480, 72), (360, 71), (160, 67), (240, 69), (360, 71), (480, 72)]

def get_chords_and_voicings(song, measure_length=960, key=None):
    chord_predictor = ChordPredictor(song, measure_length, key)

    chord_progs = chord_predictor.get_all_possible_chord_progs()

    chords_4 = chord_predictor.get_best_chord_prog(chord_progs, matrix)
    chords = chords_4[0]

    voicings = []
    for i in range(len(chords)):
        chord = chords[i]
        if i == 0:
            voice_predictor = VoicePredictor(chord, chord_predictor.key)
            voicings.append(voice_predictor.get_initial_voicing())
        else:
            voice_predictor = VoicePredictor(chord, chord_predictor.key, voicings[i-1])
            voicings.append(voice_predictor.get_best_voicing())

    dictionary = create_note_sequencers(voicings, 960)
    dictionary["solo"] = song
    return dictionary
