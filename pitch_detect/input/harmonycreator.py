import sys
import itertools
sys.path.append('..')

# we should go through these and figure out what we need
from common.constants import *
from math import *

from random import randint, random
import numpy as np

# takes in int representing midi pitch
class PitchClass(object):
    def __init__(self, midi):
        super(PitchClass)
        self.pitch_class = midi % 12

    def contains(self, midi):
        return (midi % 12 == self.pitch_class)

    def get_notes_in_range(self, pitch_range):
        # find all the octaves of this pitch class in pitch_range
        ret = range(pitch_range[0], pitch_range[1])
        ret = [i for i in ret if self.contains(i)]
        return ret

    def __str__(self):
        return PITCH_CLASS_NAMES[self.pitch_class]

# pitch is midi, scale_type is either major, harmonic minor, natural minor
class Key(object):
    def __init__(self, pitch, scale_type):
        super(Key, self).__init__()
        self.pitch = pitch
        self.scale_type = scale_type
        if scale_type in SCALES.keys():
            self.scale = SCALES[scale_type]
        else:
            self.scale = []

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
# chord_type is MAJ, MIN, DIM, AUG, or SUS4
class Chord(object):
    def __init__(self, semitones_above_key, chord_type):
        super(Chord, self).__init__()
        self.semitones_above_key = semitones_above_key
        if chord_type in CHORD_TYPES.keys():
            self.chord_pitches = CHORD_TYPES[chord_type]
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
        for x in self.get_chord_in_key(Key(60, MAJOR)):
            ret += str(x) + ' '
        return ret

    def __eq__(self, other):
        return str(self) == str(other)


# transition matrix is:
# 1-D np array of start probabilities
# 2-D np array of transition probabilities
# 1-D np array of end probabilities
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


# constants for ChordPredictor
MAT_CHORDS = []
for i in range(12):
    MAT_CHORDS.append(Chord(i, "MAJ"))
    MAT_CHORDS.append(Chord(i, "MIN"))
    MAT_CHORDS.append(Chord(i, "DIM"))
    MAT_CHORDS.append(Chord(i, "AUG"))
    MAT_CHORDS.append(Chord(i, "SUS4"))
POP_MATRIX = read_matrix(PATH_TO_DATA + '/pop.txt')



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
        minor_fit = []
        for i in range(12):
            major_scale = Key(i, MAJOR)
            minor_scale = Key(i, HARMONIC_MINOR)
            major_fit.append(major_scale.get_consonance(self.song))
            minor_fit.append(minor_scale.get_consonance(self.song))
        if max(major_fit) >= max(minor_fit):
            key = major_fit.index(max(major_fit))
            return Key(key, MAJOR)
        else:
            key = minor_fit.index(max(minor_fit))
            return Key(key, HARMONIC_MINOR)

    # measure_length given in ticks
    # TODO, make sure to pad song with enough rest so it doesn't go out of time
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

    # calculate most consonant chords at measures[idx]
    # returns array c where c[i] = 1 means MAT_CHORDS[i] is most consonant
    def calculate_consonant_chords(self, idx):
        if idx >= len(self.measures) or idx < 0:
            return []
        measure = self.measures[idx]
        chord_consonance = []
        for chord in MAT_CHORDS:
            chord_consonance.append(chord.get_consonance(measure, self.key))
        max_val = max(chord_consonance)
        ret = [1 if val == max_val else 0 for val in chord_consonance]
        return ret

    def get_top_few_chords(self, idx, few=3):
        # TODO: use different matrices?
        matrix = POP_MATRIX
        consonant_filter = self.calculate_consonant_chords(idx)
        probs = []
        for i in range(len(MAT_CHORDS)):
            probs.append(sum(matrix[1][:][i])*consonant_filter[i])
        probs_unsorted = probs[:]
        probs_sorted = sorted(set(probs), reverse=True)
        top_few = []
        for i in range(few):
            # take indices starting at 1 because first one is 0
            top_few.append(MAT_CHORDS[probs_unsorted.index(probs_sorted[i+1])])
        return top_few

    def get_all_possible_chord_progs(self, branching_factor=3):
        chords = []
        for i in range(len(self.measures)):
            chords.append(self.get_top_few_chords(i, branching_factor))
        return list(itertools.product(*chords))

    def get_best_few_chord_progs(self, chord_progs, few=4):
        # TODO: use different matrices?
        matrix = POP_MATRIX
        fits = []
        fit = 0
        for chords in chord_progs:
            fit = matrix[0][MAT_CHORDS.index(chords[0])]
            for i in range(1, len(chords)):
                fit += matrix[1][MAT_CHORDS.index(chords[i-1])][MAT_CHORDS.index(chords[i])]
            fit += matrix[2][MAT_CHORDS.index(chords[-1])]
            fits.append(fit)
        fits_unsorted = fits[:]
        fits_sorted = sorted(set(fits), reverse=True)
        best_progs = [chord_progs[fits_unsorted.index(fits_sorted[i])] for i in range(few)]
        return best_progs


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
        # voice_part -> one of SOPRANO, ALTO, TENOR, BASS
        # TODO: make this a global dictionary?

        if voice == SOPRANO:
            voice_range = [65, 72]
        elif voice == ALTO:
            voice_range = [55,65]
        elif voice == TENOR:
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
        for voice in [SOPRANO, ALTO, TENOR, BASS]:
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
            # TODO make this cleaner
            for voice in [SOPRANO, ALTO, TENOR, BASS]:
                index = VOICE_MAP[voice]
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
        return "soprano: {}, alto: {}, tenor: {}, bass: {}".format(self.soprano, self.alto, self.tenor, self.bass)


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

    return {SOPRANO: sop, ALTO: alt, TENOR: ten, BASS: bas}

def get_chords_and_voicings(song, measure_length=960, key=None, branching_factor=3, num_options=4):
    chord_predictor = ChordPredictor(song, measure_length, key)

    chord_progs = chord_predictor.get_all_possible_chord_progs(branching_factor)

    top_few = chord_predictor.get_best_few_chord_progs(chord_progs, num_options)

    top_voicings = []
    for j in range(len(top_few)):
        voicings = []
        chords = top_few[j]
        for i in range(len(chords)):
            chord = chords[i]
            if i == 0:
                voice_predictor = VoicePredictor(chord, chord_predictor.key)
                voicings.append(voice_predictor.get_initial_voicing())
            else:
                voice_predictor = VoicePredictor(chord, chord_predictor.key, voicings[i-1])
                voicings.append(voice_predictor.get_best_voicing())

        dictionary = create_note_sequencers(voicings, measure_length)
        dictionary[SOLO] = song
        top_voicings.append(dictionary)
    return top_voicings
