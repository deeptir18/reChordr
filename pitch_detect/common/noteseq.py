#####################################################################
#
# noteseq.py
#
# Copyright (c) 2017, Eran Egozy
#
# Released under the MIT License (http://opensource.org/licenses/MIT)
#
#####################################################################
from common.constants import *
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
        self.total_time = 0
        for note in self.notes:
            self.total_time += note[0]

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

    def set_rhythm(self, new_rhythm, idx):
        if idx >= 0 and idx < len(self.notes):
            (dur, pitch) = self.notes[idx]
            self.notes[idx] = (new_rhythm, pitch)

    def clear_empty_notes(self):
        new_notes = []
        for (dur, pitch) in self.notes:
            if dur != 0:
                new_notes.append((dur, pitch))
        self.notes = new_notes

    #debugging method
    def sum_rhythms(self):
        rh = [r for (r, p) in self.notes]
        return sum(rh)

    def get_song(self):
        return self.notes

    def replace_song_at_index(self, index, replacement, MEASURE_LENGTH, current_bar):
        current_song = self.notes
        print "TOTAL TIME is {}".format(self.total_time)
        total_time = 0
        for note in self.notes:
            total_time += note[0]
        assert(total_time == self.total_time, "TOTAL TIEM NOT SAME")
        # need to replace EVERYTHING in this MEASURE
        # iterate through everything including and until this index - and add up the time.
        # index we want to start at is at beginning of MEASURE
        # remove all the notes in 'current bar'
        # print "PASSED IN CURRENT BAR IS {}".format(current_bar)
        time_passed = MEASURE_LENGTH*current_bar
        time_passed_end = MEASURE_LENGTH*(current_bar + 1)
        # print "BEGIN {}, END time {}".format(time_passed, time_passed_end)
        time_so_far = 0
        change_index = 0
        change_index_end = len(self.notes) # default to end
        # print "current song is {}".format(current_song)
        for ind in range(len(current_song)):
            # print "TIME SO FAR: {}, BAR BEGIN: {}, BAR END: {}, ind: {}".format(time_so_far, time_passed, time_passed_end, ind)
            #print time_so_far, time_passed, time_passed_end
            if time_so_far == time_passed:
                change_index = ind
            elif time_so_far == time_passed_end:
                change_index_end = ind
            time_so_far += current_song[ind][0]
        # print "CHANGE INDEX: {}, change_index_end: {}".format(change_index, change_index_end)
        # print "CURRENT SONG BEFORE SLCIING: {}".format(current_song)
        # find the index of the note where the next measure starts
        begin_slice = current_song[0:change_index]
        end_slice = current_song[change_index_end:]
        # special case for end
        if change_index_end == len(self.notes): # taking out the last bar
            end_slice = []
        current_song = []
        for tup in begin_slice:
            current_song.append(tup)
        for tup in end_slice:
            current_song.append(tup)
        # print "BEGIN SLICE: {}, end_slice {}".format(begin_slice, end_slice)
        # print "Going to add: {}".format(replacement)
        # current_song = current_song[0:change_index].extend(current_song[change_index_end:])
        # print "CURRENT SONG AFTER SLCIING: {}".format(current_song)
        for i in range(change_index, change_index + len(replacement)):
            replacement_offset = i - change_index
            current_song.insert(i, replacement[replacement_offset])
        #print current_song
        self.notes = current_song

    def replace_cb_args(self, new_cb_args):
        # print self.cb_args, new_cb_args, "NEW CB ARG!!"
        self.cb_args = new_cb_args

    def set_song(self, new_song):
        self.notes = new_song

    def get_half_melody(self, top):
        half_point = WHOLE * 4
        time_passed = 0
        half_index = 0
        for i in range(len(self.notes)):
            if time_passed == half_point:
                half_index = i
            time_passed += self.notes[i][0]
        print "BOTTOM_HALF: {}, TOP half: {}".format(self.notes[half_index:], self.notes[:half_index])
        if top:
            return self.notes[:half_index]
        else:
            return self.notes[half_index:]
