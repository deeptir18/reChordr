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

class NoteSequencer(object):
    """Plays a single Sequence of notes. The sequence is a python list containing
    notes. Each note is (dur, pitch)."""
    def __init__(self, sched, synth, channel, patch, notes, loop=True, note_cb=None, cb_args=None):
        super(NoteSequencer, self).__init__()
        self.sched = sched
        self.synth = synth
        self.channel = channel
        self.patch = patch

        self.notes = notes
        self.loop = loop
        self.on_cmd = None
        self.on_note = 0
        self.playing = False
        self.note_cb = note_cb
        self.cb_args = cb_args

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
        self._note_off()

        # if looping, go back to beginning
        if self.loop and idx >= len(self.notes):
            idx = 0

        # play new note if available
        if idx < len(self.notes):
            dur, pitch = self.notes[idx]
            if pitch: # pitch 0 is a rest
                self.synth.noteon(self.channel, pitch, 60)
                self.on_note = pitch

            # schedule the next note:
            self.on_cmd = self.sched.post_at_tick(tick+dur, self._note_on, idx+1)
            if self.note_cb:
                self.note_cb(self.cb_args, idx)


    def _note_off(self):
        # terminate current note:
        if self.on_note:
            self.synth.noteoff(self.channel, self.on_note)
            self.on_note = 0

    def set_pitch(self, new_pitch, idx):
        if idx >= 0 and idx < len(self.notes):
            (dur, pitch) = self.notes[idx]
            self.notes[idx] = (dur, new_pitch)

