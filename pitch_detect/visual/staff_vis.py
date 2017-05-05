
import sys
sys.path.append('..')
from common.core import *
from common.gfxutil import *
from common.audio import *
from common.writer import *
from common.mixer import *
from common.wavegen import *
from common.synth import *
from common.clock import *
from common.metro import *
from common.noteseq import *
from notevisseq import *
from input.harmonycreator import *
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.core.window import Window
from kivy.clock import Clock as kivyClock
from kivy.uix.label import Label
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate

from random import random, randint
import numpy as np
SHARP = "sharp"
FLAT = "flat"
NATURAL = "natural"
NONE = "None"
kSomewhere = ((960, 60), (960, 72), (480, 71), (240, 67), (240, 69), (480, 71), (480, 72), )
kSomewhere_mod = ((960, 60), (480, 72), (960, 71), (240, 67), (240, 69), (480, 71), (480, 72), )
# TODO: hook this up to RHYTHMS and to note sequencers -> and try to display an entire song
# then add movement with a nowbar so it plays through the note sequence
# so make the note sequencer OPTIONALLY take in an array of these stupid staff note



STAFF_LEFT_OFFSET = 20 # offset from the left side
STAVE_SPACE_HEIGHT = 15 # height of a single space
STAVE_HEIGHT = STAVE_SPACE_HEIGHT*5
LINE_WIDTH = 1.2
SOLO = "solo"
ACCOMPANY = "accompany"
NOTES_START = 150

# draws a single Stave at the given starting position, with the right clef png, with the given pitch mapping
# pitch mapping maps pitches to heights relative to how many "clef spaces" they are away
# i.e., for treble clef, the the 1st line represents the E -> which is at the starting height, so to draw a E, the rectangle needs to start half a space below
# for treble clef -> F is at 0, E is at -.5, D is at -1, C is at -1.5, B is at -2, etc.
class Stave(InstructionGroup):
    def __init__(self, pitch_mapping,  starting_height, clef_png, clef_start, clef_size):
        super(Stave, self).__init__()
        self.bottom_offset = starting_height
        self.pitch_mapping = pitch_mapping
        # add in the clef
        self.clef_box = Rectangle(pos=clef_start, size=clef_size, source=clef_png)
        self.add(self.clef_box)

        # draw the lines
        self.lines = []
        for i in range(5):
            line_height = self.bottom_offset + i*STAVE_SPACE_HEIGHT
            line = Line(points=(STAFF_LEFT_OFFSET, line_height, Window.width, line_height), width=LINE_WIDTH)
            self.lines.append(line)
            self.add(line)

    def get_pitch_height(self, pitch):
        if pitch not in self.pitch_mapping:
            return -1 # ERROR todo: fix this to be something proper
        return self.bottom_offset + self.pitch_mapping[pitch]*STAVE_SPACE_HEIGHT


# This class instantiates 3 Single staves -> 1 in treble for solo, and 1 in treble and base for the accompaniment
# Leaves the correct amount of space in between
# Handles note placement
class TripleStave(InstructionGroup):
    def __init__(self, starting_height):
        super(TripleStave, self).__init__()
        # draw two single staves with an additional bar on the side, and a third on top for the solo
        space = 15
        self.starting_height = starting_height
        bass_clef_start = starting_height
        treble_clef_start = bass_clef_start + STAVE_HEIGHT + space

        bass_clef_png_start = (STAFF_LEFT_OFFSET, self.starting_height - 10)
        bass_clef_png_size = (100, STAVE_HEIGHT)

        treble_clef_png_start = (STAFF_LEFT_OFFSET, treble_clef_start - 10)
        treble_clef_png_size = (100, STAVE_HEIGHT)

        solo_clef_start = treble_clef_start + STAVE_HEIGHT + space
        solo_clef_png_start = (STAFF_LEFT_OFFSET, solo_clef_start - 10)
        solo_clef_png_size = (100, STAVE_HEIGHT)

        self.bass_stave = Stave(self.get_bass_pitch_mappings(), bass_clef_start, "bass-clef.png", bass_clef_png_start, bass_clef_png_size)
        self.treble_stave = Stave(self.get_treble_pitch_mappings(), treble_clef_start, "treble.png", treble_clef_png_start, treble_clef_png_size)
        self.solo_stave = Stave(self.get_treble_pitch_mappings(), solo_clef_start, "treble.png", solo_clef_png_start, solo_clef_png_size)

        self.left_line = Line(points=(STAFF_LEFT_OFFSET, self.starting_height, STAFF_LEFT_OFFSET, treble_clef_start + STAVE_HEIGHT - STAVE_SPACE_HEIGHT), width=LINE_WIDTH)
        self.solo_line = Line(points=(STAFF_LEFT_OFFSET, solo_clef_start, STAFF_LEFT_OFFSET, solo_clef_start + STAVE_HEIGHT - STAVE_SPACE_HEIGHT), width=LINE_WIDTH)

        self.treble_stave_start = treble_clef_start
        self.bass_stave_start = bass_clef_start
        self.solo_stave_start = solo_clef_start

        self.add(self.bass_stave)
        self.add(self.treble_stave)
        self.add(self.solo_stave)
        self.add(self.left_line)
        self.add(self.solo_line)

    # everything is in C major for now
    def get_treble_pitch_mappings(self):
        # F is at 0 -> so E is at -.5 and G is at + .5
        ret = {65: 0, 64: -.5, 62: -1, 60: -1.5, 67: .5, 69: 1, 71: 1.5, 72: 2, 74: 2.5, 76: 3, 78: 3.5, 79:4}
        return ret

    def get_bass_pitch_mappings(self):
        ret = {45: 0, 43: -.5, 41: -1, 40: -1.5, 47: .5, 48: 1, 50: 1.5, 52: 2, 53: 2.5, 55: 3, 57: 3.5, 59:4}
        return ret

    def get_pitch_height(self, pitch, note_type):
        bass_mappings = self.get_bass_pitch_mappings()
        treble_mappings = self.get_treble_pitch_mappings()
        if pitch not in treble_mappings and pitch not in bass_mappings:
            return "ERROR"
        if note_type == SOLO:
            if pitch not in treble_mappings:
                return "ERROR"
            return self.solo_stave.get_pitch_height(pitch)
        else:
            if pitch in treble_mappings:
                return self.treble_stave.get_pitch_height(pitch)
            else:
                return self.bass_stave.get_pitch_height(pitch)

class StaffNote(InstructionGroup):
    def __init__(self, pitch, stave, x_start, x_end, note_type, color):
        super(StaffNote, self).__init__()
        # create a dictionary of midi pitches
        # calculate the height from the pitch
        self.x_start = x_start
        self.stave = stave
        self.color = Color(color[0], color[1], color[2], .5)
        self.add(self.color)
        self.padding = .25*(x_end - x_start)
        self.fake_start = x_start + self.padding
        self.length = x_end - self.padding - self.fake_start

        self.size = (self.length, STAVE_SPACE_HEIGHT)
        self.pos = (self.fake_start, self.get_height(pitch, note_type))
        print self.size, self.pos
        self.rectangle = Rectangle(pos = self.pos, size=self.size)
        self.add(self.rectangle)

    def get_height(self, pitch, note_type):
        # return the height from the stave
        return self.stave.get_pitch_height(pitch, note_type)


    def change_alpha(self, on):
        if on:
            self.color.a = 1
        else:
            self.color.a = .5


class Barline(InstructionGroup):
    def __init__(self, stave, x_pos):
        super(Barline, self).__init__()
        # add four bars onto this stave
        self.stave = stave
        self.x_pos = x_pos # offset from "Note start"
        self.solo_barline = Line(points=(x_pos, self.stave.solo_stave_start, x_pos, self.stave.solo_stave_start + STAVE_HEIGHT - STAVE_SPACE_HEIGHT), width=LINE_WIDTH)
        self.accompany_barline = Line(points=(x_pos, self.stave.bass_stave_start, x_pos, self.stave.treble_stave_start + STAVE_HEIGHT - STAVE_SPACE_HEIGHT), width=LINE_WIDTH)
        self.add(self.solo_barline)
        self.add(self.accompany_barline)

class MainWidget2(BaseWidget) :
    def __init__(self):
        super(MainWidget2, self).__init__()
        somewhere = kSomewhereExample()
        lines = ["BASS", "TENOR", "ALTO", "SOPRANO", "solo"]
        note_sequences = [list(somewhere[key]) for key in lines]

        # now instantiate the music stuff
        self.bottom_stave = TripleStave(10)
        self.audio = Audio(2)
        self.tempo_map  = SimpleTempoMap(100)

        # connect scheduler into audio system

        self.synth = Synth('../../data/FluidR3_GM.sf2')
        self.sched = AudioScheduler(self.tempo_map)
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)
        self.patch = (0, 42)
        self.top_stave = TripleStave(Window.height/2)
        self.canvas.add(self.bottom_stave)
        self.canvas.add(self.top_stave)
        self.bar_length = (Window.width - NOTES_START)/4.0
        self.measure_time = 960
        self.playing = False
        x_pos = NOTES_START
        for i in range(4):
            self.canvas.add(Barline(self.top_stave, x_pos))
            self.canvas.add(Barline(self.bottom_stave, x_pos))
            x_pos += self.bar_length

        self.colors = [(1, 1, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)]
        self.patches = [(0, 42), (0,41), (0, 40), (0,40), (0, 4), (0, 0), (0, 0)]

        self.num_channels = 5
        self.note_sequences = [NoteSequencer(self.sched, self.synth, channel=i+1, patch = self.patches[i], notes = note_sequences[i], loop=True, note_cb=None, note_staffs=self.render_note_sequence(note_sequences[i], lines[i], self.colors[i])) for i in range(self.num_channels)]




    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'p':
            self.playing = not self.playing

        if keycode[1] == 's':
            if not self.playing:
                self.playing = True
                for ns in self.note_sequences:
                    ns.start()



    def render_note_sequence(self, seq, note_type, color): # renders a 4 bar note sequence
        print seq
        self.time_passed = 0
        self.note_staffs = []
        if note_type == "solo": # fix the constants TODO
            note_type == SOLO
        else:
            note_type = ACCOMPANY
        if note_type == SOLO:
            color = (.2, .5, .5)
        else:
            color = color
        for note in seq:
            length = note[0]
            start = (self.time_passed/(960*4.0))*(Window.width - NOTES_START) + NOTES_START
            end = start + length/(960*4.0)*(Window.width - NOTES_START)

            pitch = note[1]
            note = StaffNote(pitch, self.top_stave, start, end, note_type, color)
            self.note_staffs.append(note)
            self.canvas.add(note)
            self.time_passed += length
        return self.note_staffs


    def on_update(self) :
        if self.playing:
            self.audio.on_update()


run(MainWidget2)
