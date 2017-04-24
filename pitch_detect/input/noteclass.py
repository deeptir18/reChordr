# base class for how we represent notes
import sys
sys.path.append('..')

from common.core import *
from common.audio import *
from common.writer import *
from common.mixer import *
from common.gfxutil import *
from common.wavegen import *
from common.synth import *
from common.clock import *
from common.metro import *
from common.noteseq import *
from common.buffers import *
from common.pitchdetect import *
from math import *

 # extra information ->
 # for each pitch - has what pitches it could have been
 # absolute pitch and what relative pitch says it should be
 # what note its closest to in the key
 # for rhythm - have rhythms from last beat_rhythm
 # possibly rhythm confidence, pitch confidence

class TimeSig(object):
    def __init__(self, top, bottom):
        self.top = top
        self.bottom = bottom
class Pitch(object):
    def __init__(self, abs_pitch, abs_confidence, rel_pitch, rel_confidence):
        self.abs_pitch = abs_pitch
        self.rel_pitch = rel_pitch
        self.abs_confidence = abs_confidence
        self.rel_confidence = rel_confidence

    def get_best_guess(self):
        if self.abs_confidence > self.rel_confidence:
            return int(self.abs_pitch)
        else:
            return int(self.rel_pitch)

class NoteInfo(object):
    def __init__(self, pitch, duration):
        self.pitch_info = pitch
        self.duration = duration

    def guess(self):
        return (duration, pitch.get_best_guess())

class NoteSong(object):
    def __init__(self, time_sig, tempo):
        self.time_sig = time_sig
        self.tempo = tempo
        self.voices = {"solo": [] }

    def add_to_solo_voice(self, noteinfo):
        self.voices["solo"].append(noteinfo)

    def create_note_sequencers(self):
        ret = {}
        for voice in self.voices:
            tup = ()
            for note_info in self.voices[voice]:
                tup += (note_info.guess(),)
            ret[voice] = tup
        return ret
