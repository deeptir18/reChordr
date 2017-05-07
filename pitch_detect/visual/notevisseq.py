#####################################################################
#
# noteseq.py
#
# Copyright (c) 2017, Eran Egozy
#
# Released under the MIT License (http://opensource.org/licenses/MIT)
#
#####################################################################

import sys
sys.path.append('..')
from common.clock import kTicksPerQuarter, quantize_tick_up
from common.gfxutil import *
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line

class MovingRectangle(InstructionGroup):
    def __init__(self, pos, width, height, rgb):
        super(MovingRectangle, self).__init__()
        self.rgb = rgb
        self.color = Color(*rgb)
        self.add(self.color)

        self.rectangle = Rectangle(pos = pos, size=(width, height))
        self.add(self.rectangle)
        self.width = width
        #self.height = height

        self.time = 0
        self.on_update(0)

        self.passed = False

    def set_ypos(self, ypos):
        (x, y) = self.rectangle.pos
        self.rectangle.pos = (x, ypos)

    def highlight(self):
        self.color.rgb = (1, 1, 1)

    def un_highlight(self):
        self.color.rgb = self.rgb

    def on_update(self, dt):
        # animate position
        (x, y) = self.rectangle.pos
        self.rectangle.pos = (x-1, y)
        if x < 100 and not self.passed:
            self.passed = True
            (a, b, c) = self.color.rgb
            self.rgb = (0.3*a, 0.3*b, 0.3*c)
            self.color.rgb = self.rgb
        # advance time
        self.time += dt
        # continue flag
        return x > -self.width
        #return True

class NoteVisSequencer(InstructionGroup):
    """Plays a single Sequence of notes. The sequence is a python list containing
    notes. Each note is (dur, pitch)."""
    def __init__(self, sched, synth, channel, patch, notes, height, rgb, loop=True):
        super(NoteVisSequencer, self).__init__()
        self.sched = sched
        self.synth = synth

        self.channel = channel
        self.patch = patch
        self.volume = 60
        self.notes = notes
        self.loop = loop

        self.on_cmd = None
        self.on_rect = None
        self.on_note = 0
        self.playing = False

        self.height = height
        self.rgb = rgb
        self.note_rectangles = [MovingRectangle((Window.width-100, self.height+pitch*1.5-50), dur*0.05, 5, self.rgb) for (dur, pitch) in notes]
        self.rectangles = AnimGroup()
        self.add(self.rectangles)

        self.cur_idx = 0

    def set_volume(self, vol):
        self.volume = vol

    def start(self):
        if self.playing:
            return

        self.playing = True
        self.synth.program(self.channel, self.patch[0], self.patch[1])

        # post the first note on the next quarter-note:
        now = self.sched.get_tick()
        tick = quantize_tick_up(now, kTicksPerQuarter)
        self.on_rect = self.sched.post_at_tick(tick, self._rectangle, 0)
        self.on_cmd = self.sched.post_at_tick(tick+6100, self._note_on, 0)

    def stop(self):
        if not self.playing:
            return

        self.playing = False
        self.sched.remove(self.on_cmd)
        self.on_cmd = None
        self.sched.remove(self.on_rect)
        self.on_rect = None
        self._note_off()

    def toggle(self):
        if self.playing:
            self.stop()
        else:
            self.start()

    def _note_on(self, tick, idx):
        # terminate current note:
        self._note_off()

        # if looping, go back to beginning
        if self.loop and idx >= len(self.notes):
            idx = 0
            self.cur_idx = 0

        # play new note if available
        if idx < len(self.notes):
            dur, pitch = self.notes[idx]
            if pitch: # pitch 0 is a rest
                self.synth.noteon(self.channel, pitch, vel=self.volume)
                self.on_note = pitch

            #graphics
            #self.rectangles.add(MovingRectangle((100, self.height+pitch), dur*0.05, 5, self.rgb))

            # schedule the next note:
            self.cur_idx += 1
            self.on_cmd = self.sched.post_at_tick(tick+dur, self._note_on, idx+1)

    def _rectangle(self, tick, idx):
        if self.loop and idx >= len(self.notes):
            idx = 0
            self.note_rectangles = [MovingRectangle((Window.width-100, self.height+pitch*1.5-50), dur*0.05, 5, self.rgb) for (dur, pitch) in self.notes]
        if idx < len(self.notes):
            dur, pitch = self.notes[idx]
            if pitch != 0:
                self.rectangles.add(self.note_rectangles[idx])
            self.on_rect = self.sched.post_at_tick(tick+dur, self._rectangle, idx+1)

    def _note_off(self):
        # terminate current note:
        if self.on_note:
            self.synth.noteoff(self.channel, self.on_note)
            self.on_note = 0

    def get_notes(self):
        return self.notes

    def set_note(self, new_pitch, note_idx):
        (dur, pitch) = self.notes[note_idx]
        self.notes[note_idx] = (dur, new_pitch)
        self.note_rectangles[note_idx].set_ypos(self.height+new_pitch*1.5-50)
        #MovingRectangle((Window.width-100, self.height+new_pitch*1.5-50), dur*0.05, 5, self.rgb)

    def up_semitone(self, note_idx):
        (dur, pitch) = self.notes[note_idx]
        self.set_note(pitch+1, note_idx)

    def down_semitone(self, note_idx):
        (dur, pitch) = self.notes[note_idx]
        self.set_note(pitch-1, note_idx)

    def highlight(self, note_idx):
        self.note_rectangles[note_idx].highlight()

    def un_highlight(self, note_idx):
        self.note_rectangles[note_idx].un_highlight()

    def current_note_index(self):
        return self.cur_idx

    def on_update(self):
        if self.playing:
            self.rectangles.on_update()
