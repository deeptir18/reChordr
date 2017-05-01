
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
from notevisseq import *
from input.harmonycreator import *
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
'''
class NoteSeqVisualizer(InstructionGroup):
    def __init__(self, note_seq, audio_ns, tempo_map, height, rgb):
        super(NoteSeqVisualizer, self).__init__()

        self.note_seq = note_seq
        self.audio_ns = audio_ns
        self.tempo_map  = tempo_map
        self.cur_idx = 0
        self.height = height

        self.rgb = rgb
        self.rectangles = AnimGroup()

        self.playing = False
        self.time = -2
        self.audio_time = 0
        self.on_update(0)

    def start(self):
        self.playing = True
        self.audio_ns.start()

    def stop(self):
        if not self.playing:
            return

        self.playing = False
        self.audio_ns.stop()

    def toggle(self):
    	if self.playing:
            self.stop()
        else:
            self.start()

    def on_update(self, dt):
        if self.playing or self.time < 0:
            self.rectangles.on_update()

            dur, pitch = self.note_seq[self.cur_idx%len(self.note_seq)]
            self.audio_time += self.tempo_map.tick_to_time(dur)
            print(self.cur_idx, dur, self.tempo_map.tick_to_time(dur), self.audio_time, self.time)
            if self.time >= self.audio_time-5:
                print("yes")
                self.rectangles.add(MovingRectangle((100, self.height+pitch), dur*0.03, 5, self.rgb))

            self.cur_idx += 1
            self.time += dt

        # continue flag
        return True
'''
quarter = kTicksPerQuarter

diamonds_melody = [(quarter*1.5, 0), (quarter*0.5, 62), (quarter*0.5, 64), (quarter*0.25, 57), (quarter*0.25, 57), (quarter*0.25, 62), (quarter*0.25, 64), (quarter*0.5, 64), (quarter, 64),
(quarter*0.5, 64), (quarter*0.5, 64), (quarter*0.5, 64), (quarter*0.25, 64), (quarter*0.5, 64), (quarter*0.75, 62), (quarter, 0),
(quarter*0.25, 62), (quarter*0.5, 62), (quarter*0.75, 62), (quarter*0.5, 0), (quarter*0.25, 62), (quarter*0.5, 62), (quarter*0.75, 62), (quarter, 0),
(quarter*0.25, 60), (quarter*0.25, 60), (quarter*0.5, 62), (quarter*0.5, 62), (quarter*0.5, 62), (quarter*0.5, 64), (quarter, 57),
(quarter*0.5, 0), (quarter*0.5, 62), (quarter*0.5, 64), (quarter*0.25, 57), (quarter*0.25, 57), (quarter*0.25, 62), (quarter*0.25, 64), (quarter*0.5, 64), (quarter, 64),
(quarter*0.5, 64), (quarter*0.5, 64), (quarter*0.5, 64), (quarter*0.25, 64), (quarter*0.5, 64), (quarter*0.75, 62), (quarter, 0),
(quarter*0.25, 62), (quarter*0.5, 62), (quarter*0.75, 62), (quarter*0.5, 0), (quarter*0.25, 62), (quarter*0.5, 62), (quarter*0.75, 62), (quarter, 0),
(quarter*0.25, 60), (quarter*0.25, 60), (quarter*0.5, 62), (quarter*0.5, 62), (quarter*0.5, 62), (quarter*0.5, 64), (quarter, 57),
(quarter, 64), (quarter, 62), (quarter, 65), (quarter, 64), (quarter, 57), (quarter, 57), (quarter, 64), (quarter*0.5, 64), (quarter*0.25, 64), (quarter*1.5, 62),
(quarter*6.75, 0),
(quarter, 64), (quarter, 62), (quarter, 65), (quarter, 64), (quarter, 57), (quarter, 57), (quarter, 64), (quarter*0.5, 64), (quarter*0.25, 64), (quarter*1.5, 62), (quarter*1.75, 0)]

diamonds_soprano = [(quarter*4, 72), (quarter*4, 72), (quarter*4, 74), (quarter*4, 74), (quarter*4, 60), (quarter*2, 64), (quarter*2, 64), (quarter*2, 67), (quarter*2, 71), (quarter, 74), (quarter*3, 0), (quarter*4, 72), (quarter*4, 76), (quarter*4, 74),
(quarter*0.5, 72), (quarter*0.25, 72), (quarter*1.5, 71), (quarter*1.75, 0), (quarter*4, 60), (quarter*2, 64), (quarter*2, 64), (quarter*2, 67), (quarter*2, 0)]
diamonds_mezzo = [(quarter*4, 69), (quarter*4, 69), (quarter*4, 71), (quarter*4, 71), (quarter*2, 65), (quarter*2, 69), (quarter*2, 69), (quarter*2, 69), (quarter*4, 71), (quarter, 67), (quarter*3, 0), (quarter*4, 69), (quarter*4, 72), (quarter*4, 71),
(quarter*0.5, 69), (quarter*0.25, 69), (quarter*1.5, 67), (quarter*1.75, 0), (quarter*2, 65), (quarter*2, 69), (quarter*2, 69), (quarter*2, 69), (quarter*2, 71), (quarter*2, 0)]
diamonds_alto = [(quarter*4, 65), (quarter*4, 64), (quarter*4, 67), (quarter*4, 67), (quarter*2, 57), (quarter*2, 57), (quarter*2, 60), (quarter*2, 60), (quarter*4, 59), (quarter, 59), (quarter*3, 0), (quarter*4, 65), (quarter*4, 69), (quarter*4, 67),
(quarter*0.5, 65), (quarter*0.25, 65), (quarter*1.5, 64), (quarter*1.75, 0), (quarter*2, 57), (quarter*2, 57), (quarter*2, 60), (quarter*2, 60), (quarter*2, 59), (quarter*2, 0)]
diamonds_tenor = [(quarter*16, 0), (quarter*2, 53), (quarter*2, 57), (quarter*2, 57), (quarter*2, 60), (quarter*4, 62), (quarter, 62), (quarter*3, 0), (quarter*4, 60), (quarter*4, 57), (quarter*4, 55),
(quarter*2.25, 60), (quarter*1.75, 0), (quarter*2, 53), (quarter*2, 57), (quarter*2, 57), (quarter*2, 60), (quarter*2, 62), (quarter*2, 0)]
diamonds_bass = [(quarter*16, 0), (quarter*4, 29), (quarter*4, 33), (quarter*4, 31), (quarter, 31), (quarter, 0), (quarter, 33), (quarter, 31), (quarter*4, 29), (quarter*4, 33), (quarter*4, 31), (quarter*4, 0), (quarter*4, 29), (quarter*4, 33), (quarter*2, 31), (quarter*2, 0)]
diamonds_perc = [(quarter*32, 0), (quarter*0.75, 36), (quarter*0.75, 38), (quarter, 36), (quarter*0.5, 36), (quarter*0.5, 38), (quarter*0.25, 42), (quarter*0.25, 42),
(quarter*0.75, 36), (quarter*0.75, 38), (quarter, 36), (quarter*0.5, 36), (quarter*0.5, 38), (quarter*0.25, 42), (quarter*0.25, 42),
(quarter*0.75, 36), (quarter*0.75, 38), (quarter, 36), (quarter*0.5, 36), (quarter*0.5, 38), (quarter*0.25, 42), (quarter*0.25, 42),
(quarter*0.75, 42), (quarter*0.75, 42), (quarter, 42), (quarter*1.5, 0),
(quarter*0.75, 36), (quarter*0.75, 38), (quarter, 36), (quarter*0.5, 36), (quarter*0.5, 38), (quarter*0.25, 42), (quarter*0.25, 42),
(quarter*0.75, 36), (quarter*0.75, 38), (quarter, 36), (quarter*0.5, 36), (quarter*0.5, 38), (quarter*0.25, 42), (quarter*0.25, 42),
(quarter*0.75, 36), (quarter*0.75, 38), (quarter, 36), (quarter*0.5, 36), (quarter*0.5, 38), (quarter*0.25, 42), (quarter*0.25, 42)]

note_sequences = [diamonds_perc, diamonds_bass, diamonds_tenor, diamonds_alto, diamonds_mezzo, diamonds_soprano, diamonds_melody]
somewhere = kSomewhereExample()
lines = ["BASS", "TENOR", "ALTO", "SOPRANO", "solo"]
note_sequences = [list(somewhere[key]) for key in lines]

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()
        print kSomewhereExample()

        self.info = Label(text = "text", valign='top', font_size='18sp',
              pos=(Window.width * 0.8, Window.height * 0.4),
              text_size=(Window.width, Window.height))
        self.add_widget(self.info)

        self.audio = Audio(2)
        self.synth = Synth('../../data/FluidR3_GM.sf2')

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(100)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)

        # create the metronome:
        self.metro = Metronome(self.sched, self.synth)

        self.colors = [(1, 1, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)]
        self.patches = [(0, 42), (0,41), (0, 40), (0,40), (0, 4), (0, 0), (0, 0)]
        self.parts = ["Percussion", "Bass", "Tenor", "Alto", "Mezzo", "Soprano", "Melody"]
        self.num_channels = 5
        self.note_sequences = [NoteVisSequencer(self.sched, self.synth, channel = i+1, patch = self.patches[i], notes = note_sequences[i], height=(Window.height-40)/float(self.num_channels)*i+20, rgb = self.colors[i]) for i in range(self.num_channels)]


        #self.note_sequences = [NoteSeqVisualizer(note_seq=note_sequences[i], audio_ns=NoteSequencer(self.sched, self.synth, channel=i+1, patch = self.patches[i], notes = note_sequences[i]), tempo_map=self.tempo_map, height=(Window.height-40)/float(self.num_channels)*i+20, rgb=self.colors[i]) for i in range(self.num_channels)]
        #self.note_sequences = [NoteSeqVisualizer(note_seq=note_sequences[0], audio_ns=NoteSequencer(self.sched, self.synth, channel=0+1, patch = self.patches[0], notes = note_sequences[0]), tempo_map=self.tempo_map, height=(Window.height-40)/float(self.num_channels)*0+20, rgb=self.colors[0])]
        #self.anim_group = AnimGroup()
        #for ns in self.note_sequences:
        #    self.anim_group.add(ns)


        for ns in self.note_sequences:
            self.canvas.add(ns)

        self.nowbar = Line(points=(100, 0, 100, Window.height), width=2)
        self.canvas.add(Color(0.545, 0.27, 0.0745))
        self.canvas.add(self.nowbar)

        self.playing = False
        self.changing = False
        self.change_idx = 0
        self.note_sequences[0].set_volume(30)
        self.note_sequences[1].set_volume(40)
        self.note_sequences[2].set_volume(60)
        self.note_sequences[3].set_volume(70)
        self.note_sequences[4].set_volume(90)



    def on_update(self) :
        if self.playing:
            self.audio.on_update()
            #self.anim_group.on_update()
            for ns in self.note_sequences:
                ns.on_update()

        #self.info.text = "Playing: " + str(self.playing) +"\n"
        #self.info.text += "Change Pitches: " + str(self.changing) + "\n"
        self.info.text = ""
        if self.changing:
            self.info.text += "Changing: " + self.parts[self.change_idx]

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'm':
            self.metro.toggle()

        if keycode[1] == 'p':
            self.changing = False
            self.playing = not self.playing

        if keycode[1] == 's':
            if not self.playing:
                self.playing = True
                for ns in self.note_sequences:
                    ns.start()

        if keycode[1] == 'c':
            if not self.playing:
                self.changing = not self.changing

        if keycode[1] == 'up':
            if self.changing:
                self.change_idx = (self.change_idx+1)%self.num_channels

        if keycode[1] == 'down':
            if self.changing:
                self.change_idx = (self.change_idx-1)%self.num_channels

# pass in which MainWidget to run as a command-line arg
run(MainWidget)
