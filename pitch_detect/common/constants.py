# Controls for different modes
SET_TEMPO_MODE = 0
SOLO_TRANSCRIBE_MODE = 1
SOLO_EDIT_MODE = 2
CHORD_GENERATION_MODE = 3

METRO_CHANNEL = 0
DEFAULT_TEMPO = 60
RHYTHM_PROFILE = [2.5, 2.5, 2.5, 3.7, 4.5, 4.5, 7.7, 7.7, 8.3, 9.5, 9.5, 9.5]
PATH_TO_SYNTH = '../data/FluidR3_GM.sf2'

COLORS = [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 1), (0, 1, 0)]
PATCHES = [(0, 42), (0,41), (0, 40), (0,40), (0, 4)]
PARTS = ["bass", "tenor", "alto", "soprano", "solo"]
PART_CHANNELS = [1, 2, 3, 4, 5]
PART_VOLUMES = [50, 50, 50, 50, 120]
# maybe need an assert statement here
NUM_PARTS = 5

BASS, TENOR, ALTO, SOPRANO, SOLO = PARTS
MAJOR = 'MAJOR'
HARMONIC_MINOR = 'HARMONIC_MINOR'
NATURAL_MINOR = 'NATURAL_MINOR'

# this seems unnecessary
VOICE_MAP ={SOPRANO: 0, ALTO: 1, TENOR: 2, BASS: 3}
SCALES={MAJOR: (0, 2, 4, 5, 7, 9, 11), HARMONIC_MINOR: (0, 2, 3, 5, 7, 8, 11), NATURAL_MINOR: (0, 2, 3, 5, 7, 8, 10)}
CHORD_TYPES={"MAJ": (0, 4, 7), "MIN": (0, 3, 7), "DIM": (0, 3, 6), "AUG": (0, 4, 8), "SUS4": (0, 5, 7)}
PITCH_CLASS_NAMES = ['C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B']

