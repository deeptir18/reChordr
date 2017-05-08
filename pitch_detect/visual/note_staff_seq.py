#####################################################################
#
# noteseq.py
#
# Copyright (c) 2017, Eran Egozy
#
# Released under the MIT License (http://opensource.org/licenses/MIT)
#
#####################################################################

from common.clock import kTicksPerQuarter, quantize_tick_up

class NoteStaffSequencer(object):
    """Plays a single Sequence of notes. The sequence is a python list containing
    notes. Each note is (dur, pitch)."""
    def __init__(self, sched, synth, channel, patch, notes, part, loop=True, note_cb=None, note_staffs=None):
        super(NoteStaffSequencer, self).__init__()
        self.sched = sched
        self.synth = synth
        self.channel = channel
        self.patch = patch
        self.part = part

        self.note_cb = note_cb
        self.notes = notes
        self.loop = loop
        self.on_cmd = None
        self.on_note = 0
        self.playing = False
        self.visualize=False
        if note_staffs != None:
            self.note_staffs = note_staffs
            assert(len(self.note_staffs) == len(self.notes))
            self.visualize = True

        self.cur_idx = 0

    def start(self):
        if self.playing:
            return

        self.playing = True
        self.synth.program(self.channel, self.patch[0], self.patch[1])

        # post the first note on the next quarter-note:
        now = self.sched.get_tick()
        tick = quantize_tick_up(now, kTicksPerQuarter)
        self.on_cmd = self.sched.post_at_tick(tick, self._note_on, 0)

    def stop(self):
        if not self.playing:
            return

        self.playing = False
        self.sched.remove(self.on_cmd)
        self.on_cmd = None
        self._note_off()

    def toggle(self):
        if self.playing:
            self.stop()
        else:
            self.start()

    def _note_on(self, tick, idx):
        # terminate current note:
        self.note_staffs[(idx-1)%len(self.notes)].change_alpha(False)
        self._note_off()


        # if looping, go back to beginning
        if self.loop and idx >= len(self.notes):
            idx = 0
            self.cur_idx = 0

        # play new note if available
        if idx < len(self.notes):
            dur, pitch = self.notes[idx]
            if pitch: # pitch 0 is a rest
            # visualize the note staffs if this is an option:
                if self.visualize:
                    staff_note = self.note_staffs[idx]
                    staff_note.change_alpha(True)
                self.synth.noteon(self.channel, pitch, 60)
                self.on_note = pitch

            # schedule the next note:
            self.cur_idx += 1
            self.on_cmd = self.sched.post_at_tick(tick+dur, self._note_on, idx+1)
            if self.note_cb:
                self.note_cb(idx)


    def _note_off(self):
        # terminate current note:
        if self.on_note:
            self.synth.noteoff(self.channel, self.on_note)
            self.on_note = 0

    def get_notes(self):
        return self.notes

    def get_cur_pitch(self, note_idx):
        return self.notes[note_idx][1]

    def set_note(self, new_pitch, note_idx):
        (dur, pitch) = self.notes[note_idx]
        self.notes[note_idx] = (dur, new_pitch)
        self.note_staffs[note_idx].set_note(new_pitch, self.part)
        #self.note_rectangles[note_idx].set_ypos(self.height+new_pitch*1.5-50)

    def up_semitone(self, note_idx):
        (dur, pitch) = self.notes[note_idx]
        self.set_note(pitch+1, note_idx)

    def down_semitone(self, note_idx):
        (dur, pitch) = self.notes[note_idx]
        self.set_note(pitch-1, note_idx)

    def highlight(self, note_idx):
        self.note_staffs[note_idx].highlight()

    def un_highlight(self, note_idx):
        self.note_staffs[note_idx].un_highlight()

    def current_note_index(self):
        return self.cur_idx
