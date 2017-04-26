import mido
from common.core import *
from common.audio import *
from common.writer import *
from common.mixer import *
from common.gfxutil import *
from common.wavegen import *
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate

class MovingRectangle(InstructionGroup):
	def __init__(self, pos1, width, height, color):
		super(MovingRectangle, self).__init__()

		#self.color = color
		#self.add(self.color)

		self.rectangle = Rectangle(pos = pos1, size=(width, height))
		self.add(self.rectangle)
		self.width = width
		#self.height = height

		self.time = 0
		#self.on_update(0)

	def on_update(self, dt):
		# animate position
		#(x, y) = self.rectangle.pos
		#print((x, y))
		#self.rectangle.pos = (x-1, y)
		#self.rectangle = Rectangle(pos = pos, length=(self.width, self.height))

		# advance time
		self.time += dt
		# continue flag
		#return x > -self.width
		return True

class MidiVisualizer(InstructionGroup):
    def __init__(self, midi, max_channels):
        super(MidiVisualizer, self).__init__()

        self.mid = mido.MidiFile(midi)
        self.max_channels = max_channels
        self.port = mido.open_output()
        self.messages = self.mid.play()

        self.colors = [Color((1., 0., 0.)), Color((0., 1., 0.)), Color((0., 0., 1.)), Color((1., 1., 0.)), Color((1., 0., 1.)), Color((0., 1., 1.)), Color((1., 1., 1.))]
        self.rectangles = AnimGroup()

        self.playing = False

    def toggle(self):
    	self.playing = not self.playing
    	print("Playing: " + str(self.playing))

    def play(self):
    	self.playing = True

    def pause(self):
    	self.playing = False

    def on_update(self):
        if self.playing:
        	self.rectangles.on_update()

        	msg = self.messages.next()
	        self.port.send(msg)

	        tokens = str(msg).strip().split(' ')
	        if (tokens[0] == 'note_on'):
		        channel = int(tokens[1][tokens[1].index('=')+1:])
		        note = int(tokens[2][tokens[2].index('=')+1:])
		        time = float(tokens[4][tokens[4].index('=')+1:])

		        #rectangles
		        self.rectangles.add(MovingRectangle((100, Window.height/self.max_channels*channel+note), time*100, 5, self.colors[channel%len(self.colors)]))
		        #self.add(self.colors[channel%len(self.colors)])
		        #self.add(Color((1., 1., 0., 0.5)))
		        #self.add(Rectangle(pos=(100, Window.height/self.max_channels*channel+note), size=(time*100, 5)))

        # continue flag
        return True

class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        self.info = topleft_label()
        self.add_widget(self.info)

        self.mid = MidiVisualizer('song.mid', 10)

        self.canvas.add(self.mid)

    def on_update(self) :
    	self.mid.on_update()
        self.info.text = 'fps:%d\n' % kivyClock.get_fps()

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'p':
            self.mid.toggle()

# pass in which MainWidget to run as a command-line arg
run(MainWidget)