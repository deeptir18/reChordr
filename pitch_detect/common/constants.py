from common.clock import kTicksPerQuarter
from kivy.core.window import Window
Window.fullscreen = True

TEST_SONG = [[960, 60], [960, 72], [480, 71], [240, 67], [240, 69], [480, 71], [480, 72],
						 [960, 60], [960, 69], [960*2, 67], [960, 57], [960, 65], [480, 64], [240, 60],
						 [240, 62], [480, 64], [480, 65], [480, 64], [240, 59], [240, 60], [480, 62], [480, 64],
						 [960*2, 60], [480, 0]]


# FOR rendering
MEASURE_LENGTH = kTicksPerQuarter*4
QUARTER = 480.0
HALF = QUARTER * 2.0
WHOLE = QUARTER * 4.0
EIGHTH = QUARTER/2.0
TRIPLET = QUARTER/3.0
SIXTEENTH = QUARTER/4.0
DOTTED_HALF = QUARTER * 3
DOTTED_QUARTER = QUARTER*1.5

# Controls for different modes
SET_TEMPO_MODE = 0
SOLO_TRANSCRIBE_MODE = 1
SOLO_EDIT_MODE = 2
CHORD_GENERATION_MODE = 3
RHYTHM_EDIT_MODE = 4
DEFAULT = "default"
# RHYTHM TEST_RHYTHM_TEMPLATES
TEST_RHYTHM_TEMPLATES = [DEFAULT]
TEST_RHYTHM_TEMPLATES.append([(EIGHTH, 1), (EIGHTH, 3), (EIGHTH, 5), (EIGHTH, 3)]*2)
TEST_RHYTHM_TEMPLATES.append([(EIGHTH, 5), (EIGHTH, 1), (EIGHTH, 3), (EIGHTH, 1)]*2)
TEST_RHYTHM_TEMPLATES.append([(TRIPLET, 1), (TRIPLET, 3), (TRIPLET, 5)]*4)

PATH_TO_DATA = '../data/'

# constants for metronome + rhythm detect
METRO_CHANNEL = 0
DEFAULT_TEMPO = 60
RHYTHM_PROFILE = [2.5, 2.5, 2.5, 3.7, 4.5, 4.5, 7.7, 7.7, 8.3, 9.5, 9.5, 9.5]
PATH_TO_SYNTH = PATH_TO_DATA + 'FluidR3_GM.sf2'

# music constants
PARTS = ["bass", "tenor", "alto", "soprano", "solo"]
BASS, TENOR, ALTO, SOPRANO, SOLO = PARTS
MAJOR = 'MAJOR'
HARMONIC_MINOR = 'HARMONIC_MINOR'
NATURAL_MINOR = 'NATURAL_MINOR'

VOICE_MAP ={SOPRANO: 0, ALTO: 1, TENOR: 2, BASS: 3} # this seems unnecessary
SCALES={MAJOR: (0, 2, 4, 5, 7, 9, 11), HARMONIC_MINOR: (0, 2, 3, 5, 7, 8, 11), NATURAL_MINOR: (0, 2, 3, 5, 7, 8, 10)}
CHORD_TYPES={"MAJ": (0, 4, 7), "MIN": (0, 3, 7), "DIM": (0, 3, 6), "AUG": (0, 4, 8), "SUS4": (0, 5, 7)}
PITCH_CLASS_NAMES = ['C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B']

MIN_PITCH = 40
MAX_PITCH = 76
MIN_TREBLE_PITCH = 60
# constants for GUI
COLORS = [(0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 1), (0, 1, 0)]
PATCHES = [(0, 42), (0,41), (0, 40), (0,40), (0, 4)]
PART_CHANNELS = [1, 2, 3, 4, 5]
PART_VOLUMES = [50, 50, 50, 50, 120]
# maybe need an assert statement here
NUM_PARTS = 5

SHARP = "sharp"
FLAT = "flat"
NATURAL = "natural"
NONE = "None"

kSomewhere = [[960, 60], [960, 74], [480, 71], [240, 67], [240, 69], [480, 71], [480, 72]]
kSomewhere_mod = [(960, 60), (480, 72), (960, 71), (240, 67), (240, 69), (480, 71), (480, 73), ]

STAFF_LEFT_OFFSET = 10 # offset from the left side
STAVE_SPACE_HEIGHT = 15 # height of a single space
STAVE_HEIGHT = STAVE_SPACE_HEIGHT*5
LINE_WIDTH = 1.2
NOTES_START = 70
NOTES_END = 10
