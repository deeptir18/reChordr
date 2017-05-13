
import sys
sys.path.append('..')
from common.constants import *
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Rectangle, Line
from input.harmonycreator import PitchClass

# TODO: hook this up to RHYTHMS and to note sequencers -> and try to display an entire song
# then add movement with a nowbar so it plays through the note sequence
# so make the note sequencer OPTIONALLY take in an array of these stupid staff note

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
            line = Line(points=(STAFF_LEFT_OFFSET, line_height, Window.width - NOTES_END, line_height), width=LINE_WIDTH)
            self.lines.append(line)
            self.add(line)

    def get_pitch_height(self, pitch):
        if pitch not in self.pitch_mapping:
            return -1. # ERROR todo: fix this to be something proper
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

        bass_clef_png_start = (STAFF_LEFT_OFFSET + 5, self.starting_height)
        bass_clef_png_size = (50, STAVE_HEIGHT*.8)

        treble_clef_png_start = (STAFF_LEFT_OFFSET + 5, treble_clef_start - 25)
        treble_clef_png_size = (50, STAVE_HEIGHT*1.3)

        solo_clef_start = treble_clef_start + STAVE_HEIGHT + space
        solo_clef_png_start = (STAFF_LEFT_OFFSET + 5, solo_clef_start - 25)
        solo_clef_png_size = (50, STAVE_HEIGHT*1.3)

        self.bass_stave = Stave(self.get_bass_pitch_mappings(), bass_clef_start, "./visual/bass1.png", bass_clef_png_start, bass_clef_png_size)
        self.treble_stave = Stave(self.get_treble_pitch_mappings(), treble_clef_start, "./visual/treble1.png", treble_clef_png_start, treble_clef_png_size)
        self.solo_stave = Stave(self.get_treble_pitch_mappings(), solo_clef_start, "./visual/treble1.png", solo_clef_png_start, solo_clef_png_size)

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
        if pitch == 0:
            return (0, False)
        if pitch < MIN_PITCH or pitch > MAX_PITCH:
            return (-1, False)# error cannot render
        # check what note this is using pitch class
        pitch_class = PitchClass(pitch)
        render_sharp = False
        if pitch_class.has_sharp():
            render_sharp = True

        bass_mappings = self.get_bass_pitch_mappings()
        treble_mappings = self.get_treble_pitch_mappings()

        if pitch not in treble_mappings and pitch not in bass_mappings:
            assert(render_sharp)
            # turn pitch the closest pitch in the dictionary down (and render sharp will be true)
            new_pitch = pitch
            while new_pitch not in treble_mappings and new_pitch not in bass_mappings:
                new_pitch -= 1
            pitch = new_pitch
        if note_type == SOLO:
            return (self.solo_stave.get_pitch_height(pitch), render_sharp)
        else:
            if pitch in treble_mappings:
                return (self.treble_stave.get_pitch_height(pitch), render_sharp)
            else:
                return (self.bass_stave.get_pitch_height(pitch), render_sharp)

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

# staves is a list of staves, returns a list of all barline objects to be drawn
def get_all_barlines(staves):
    all_barlines = []
    x_pos = NOTES_START
    # maybe not hard-code 4
    bar_length = (Window.width - NOTES_START - NOTES_END)/4.0
    
    x_pos += bar_length
    for i in range(4):
        for stave in staves:
            all_barlines.append(Barline(stave, x_pos))
        x_pos += bar_length
    return all_barlines




class StaffNote(InstructionGroup):
    def __init__(self, pitch, stave, x_start, x_end, note_type, color, part_idx, note_idx):
        super(StaffNote, self).__init__()
        self.pitch = pitch
        self.stave = stave
        self.note_type = note_type

        padding = .25*(x_end - x_start)
        self.x_start = x_start + padding

        self.length = x_end - padding - self.x_start



        self.part_idx = part_idx
        self.note_idx = note_idx

        if self.pitch == 0: # rests
            self.size = (0,0)
            self.pos = (0,0)
        else:
            self.size = (self.length, STAVE_SPACE_HEIGHT)
            self.pos = (self.x_start, self.get_height())
            self.add_sharp()

        self.color = Color(color[0], color[1], color[2], .5)
        self.default_color = color
        self.add(self.color)
        self.rectangle = Rectangle(pos = self.pos, size=self.size)
        self.add(self.rectangle)

    def add_sharp(self):
        self.sharp = Rectangle(pos = (self.pos[0] - 12, self.pos[1]), size = (10, STAVE_SPACE_HEIGHT), source="./visual/sharp.png")
        if self.has_sharp():
            self.add(Color(1,1,1))
            self.add(self.sharp)

    def remove_sharp(self):
        if self.sharp is not None:
            self.sharp.size = (0,0)


    def get_height(self):
        # return the height from the stave
        return self.stave.get_pitch_height(self.pitch, self.note_type)[0]

    def has_sharp(self):
        return self.stave.get_pitch_height(self.pitch, self.note_type)[1]

    def set_active(self, active):
        if active:
            self.color.a = 1
        else:
            self.color.a = .5

    def check_pitch(self, pitch):
        # returns true if this pitch can be rendered in this clef
        if (self.stave.get_pitch_height(pitch, self.note_type)[0] == -1):
            return False
        return True


    def set_pitch(self, new_pitch):
        self.pitch = new_pitch
        self.remove_sharp()
        self.pos = (self.x_start, self.get_height())
        self.rectangle.pos = self.pos
        self.add_sharp()

    # currently not using this
    def move_pitch(self, semitones_up):
        self.set_pitch(self.pitch + semitones_up)

    def set_highlight(self, on):
        if on:
            self.color.rgb = (0, 0, 0)
        else:
            self.color.rgb = self.default_color
            self.set_active(False)

    def _get_corners(self):
        (x1, y1) = self.rectangle.pos
        (x2, y2) = (x1 + self.size[0], y1 + self.size[1])
        return (x1, x2, y1, y2)

    def intersects(self, pos):
        (x, y) = pos
        (x1, x2, y1, y2) = self._get_corners()
        return x1 <= x and x <= x2 and y1 <= y and y <= y2

def get_staff_notes(notes, note_type, part_idx, color, stave): # renders a 4 bar note sequence
    time_passed = 0.
    staff_notes = []
    note_idx = 0

    for note in notes:
        length = note[0]
        start = (time_passed/(MEASURE_LENGTH*4.0))*(Window.width - NOTES_START - NOTES_END) + NOTES_START
        end = start + length/(MEASURE_LENGTH*4.0)*(Window.width - NOTES_START - NOTES_END)

        pitch = note[1]
        staff_note = StaffNote(pitch, stave, start, end, note_type, color, part_idx, note_idx)
        staff_notes.append(staff_note)
        time_passed += length
        note_idx += 1
    return staff_notes

# highlights StaffNote at idx within staff_note_part
def highlight_staff_note(staff_note_part, idx):
    for i in range(len(staff_note_part)):
        staff_note_part[i].set_active(False)
    staff_note = staff_note_part[idx]
    staff_note.set_active(True)

# reverts all the StaffNotes in staff_note_part to original coloring
def reset_to_default(staff_note_part):
    for staff_note in staff_note_part:
        staff_note.set_highlight(False)
        staff_note.set_active(False)
