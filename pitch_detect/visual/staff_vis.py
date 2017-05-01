
import sys
sys.path.append('..')
from common.core import *
from common.gfxutil import *

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

# TODO:
# need to take care of adding in accidentals
# also setting the key signature
# and adding the line if the note is above

class StaffNote(InstructionGroup):
    def __init__(self, pitch, rhythm, x_start, accidental, bottom_lines, top_lines):
        super(StaffNote, self).__init__()
        # create a dictionary of midi pitches
        # calculate the height from the pitch
        self.staff_bottom_offset = Window.height/4.0
        self.grand_staff_height = Window.height/4.0*2

        # ratio of space in single staffs
        self.single_staff_height = self.grand_staff_height*.75/2
        self.space_height = self.grand_staff_height*.25
        # note height
        self.note_height = self.single_staff_height/5.0

        self.height_dict = {}
        self.top_lines = top_lines
        self.bottom_lines = bottom_lines
        self.bottom_line_pitches=[43, 47, 50, 53, 57 ] #g b d f a
        self.top_line_pitches=[64, 67, 71, 74, 77] # e g b d f
        self.bottom_space_pitches=[44, 48, 51, 54, 58]
        self.top_space_pitches=[65, 69, 72, 75, 78]

        for i in range(5):
            self.height_dict[self.bottom_line_pitches[i]] = self.bottom_lines[i].points[1] - self.note_height/2.0
            self.height_dict[self.bottom_space_pitches[i]] = self.bottom_lines[i].points[1]

            self.height_dict[self.top_line_pitches[i]] = self.top_lines[i].points[1] - self.note_height/2.0
            self.height_dict[self.top_space_pitches[i]] = self.top_lines[i].points[1]

        self.x_start = x_start
        self.rgb = (.2,.5,.5)
        self.color = Color(*self.rgb)
        self.add(self.color)

        self.size = (20, self.single_staff_height/5.0)
        self.pos = (self.x_start, self.get_height(pitch))
        self.rectangle = Rectangle(pos = self.pos, size=self.size)
        self.add(self.rectangle)

    def get_height(self, pitch):
        if pitch in self.height_dict:
            return self.height_dict[pitch]
        else: # need to add a sharp
            min_dist = 0
            closest_pitch = self.height_dict.keys()[0]
            for p in self.height_dict:
                dist = abs(p - pitch)
                if dist < min_dist:
                    min_dist = dist
                    closest_pitch = p
            return self.height_dict[closest_pitch]




class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()
        self.info = Label(text = "text", valign='top', font_size='18sp',
              pos=(Window.width * 0.8, Window.height * 0.4),
              text_size=(Window.width, Window.height))
        self.add_widget(self.info)

        self.draw_staff()

    def draw_staff(self):
        self.staff_left_offset = 20
        self.staff_bottom_offset = Window.height/4.0
        self.grand_staff_height = Window.height/4.0*2

        # ratio of space in single staffs
        self.single_staff_height = self.grand_staff_height*.75/2
        self.space_height = self.grand_staff_height*.25

        start = self.staff_bottom_offset
        end = start + self.grand_staff_height
        self.staff_left = Line(points=(self.staff_left_offset, start, self.staff_left_offset, end), width=2)
        self.canvas.add(self.staff_left)

        # now two sets of 5 lines coming out
        self.bottom_lines = []
        self.top_lines = []

        # now add treble and base clef -> NOTE: need to hardcode sort of how they fit into the staff lines
        self.bass_box = Rectangle(pos=(self.staff_left_offset, self.staff_bottom_offset-10), size=(100, self.single_staff_height), source="bass-clef.png")
        self.treble_box = Rectangle(pos=(self.staff_left_offset, self.staff_bottom_offset + self.single_staff_height + self.space_height), size=(100, self.single_staff_height+20), source="treble.png")
        self.canvas.add(self.bass_box)
        self.canvas.add(self.treble_box)

        for i in range(5):
            bottom_height = self.staff_bottom_offset + i*(self.single_staff_height)/5.0
            top_height = self.staff_bottom_offset + self.single_staff_height + self.space_height + (i+1)*(self.single_staff_height)/5.0
            bottom_line = Line(points=(self.staff_left_offset, bottom_height, Window.width, bottom_height), width=2)
            top_line = Line(points=(self.staff_left_offset, top_height, Window.width, top_height), width=2)
            self.bottom_lines.append(bottom_line)
            self.top_lines.append(top_line)

            self.canvas.add(bottom_line)
            self.canvas.add(top_line)

        self.canvas.add(StaffNote(69, 0, 200, NONE, self.bottom_lines, self.top_lines))






run(MainWidget)
