#!/usr/bin/env python3
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.

import time
from neopixel import *
import argparse
import threading
from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher


# LED strip configuration:
LED_COUNT      = 100      # Number of LED pixels.
LED_PIN        = 12      # GPIO pin connected to the pixels (18 uses PWM!).
#LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
WAIT_MS        = 31.25      # min interval
PATTERN_SPLIT      = 1920.0

# Listen IP & PORT
IP = '127.0.0.1'
PORT = 6700
DEF_ROLE_SPEED = 1

class RGBData:
    def __init__(self,r=0,g=0,b=0):
        self.r = int(r)
        self.g = int(g)
        self.b = int(b)
    
    def get_color(self):
        return Color(int(self.g),int(self.r),int(self.b))

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return RGBData(g=pos * 3,r=255 - pos * 3,b=0)
    elif pos < 170:
        pos -= 85
        return RGBData(g=255 - pos * 3,r= 0,b= pos * 3)
    else:
        pos -= 170
        return RGBData(g=0,r= pos * 3,b= 255 - pos * 3)

class RGBOutput(threading.Thread):
    def __init__(self,strip):
        threading.Thread.__init__(self)
        self.rgb_mode = "rainbow"
        self.rgb_color = RGBData(255,0,0)
        self.rainbow_roll_skip = 1.0
        self.rainbow_roll_state = 0
        self.rainbow_roll_interval = 1.0
        self.pattern_mode = "none"
        self.pattern_skip = 16.0
        self.pattern_state = 0.0
        self.luminosity = 1.0
        self.strip = strip
        self.output_data = []
        
        # init output data
        for i in range(self.strip.numPixels()):
            self.output_data.append(RGBData())

        print("Finish initializing RGBOutput")

    def run(self):
        while True:
        #Color Mode Select Section
        if(self.rgb_mode == "point"):
            self.point_color()
        else:
            self.rainbow_color()

        #Lighting Pattern Select Section
        for i in range(self.strip.numPixels()):
            if(self.pattern_mode == "beat"):
                self.output_data[i] = self.generate_beat(self.output_data[i])
            elif(self.pattern_mode == "breath"):
                self.output_data[i] = self.generate_breath(self.output_data[i])
            elif(self.pattern_mode == "pulse"):
                self.output_data[i] = self.generate_pulse(self.output_data[i])
            elif(self.pattern_mode == "triangle"):
                self.output_data[i] = self.generate_triangle(self.output_data[i])
        self.pattern_state += self.pattern_skip
        if(self.pattern_state > 1920.0):
            self.pattern_state = 0

        #Luminosity Select Section
        for i in range(self.strip.numPixels()):
            self.output_data[i].r *= self.luminosity
            self.output_data[i].g *= self.luminosity
            self.output_data[i].b *= self.luminosity

        #Output Data Section
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i,self.output_data[i].get_color())
        self.strip.show()
        time.sleep(WAIT_MS/1000.0)

    def point_color(self):
        for i in range(self.strip.numPixels()):
            self.output_data[i] = self.rgb_color
    
    def rainbow_color(self):
        for i in range(self.strip.numPixels()):
            self.output_data[i] = wheel(int((float(i) * self.rainbow_roll_interval ) + self.rainbow_roll_state) & 255 )
        self.rainbow_roll_state += self.rainbow_roll_skip
        print(self.rainbow_roll_state)
        if(self.rainbow_roll_state > 255.0):
            self.rainbow_roll_state = 0
        elif(self.rainbow_roll_state < 0):
            self.rainbow_roll_state = 255.0

    def generate_beat(self,rgb_data):
        rate = int(self.pattern_state)
        return RGBData(rgb_data.r * rate, rgb_data.g * rate, rgb_data.b * rate)

    def generate_breath(self,rgb_data):
        rate = int(self.pattern_state)
        return RGBData(rgb_data.r * rate, rgb_data.g * rate, rgb_data.b * rate)

    def generate_pulse(self,rgb_data):
        if(int(self.pattern_state) < (PATTERN_SPLIT / 2)):
            rate = 1.0
        else:
            rate = 0.0
        return RGBData(rgb_data.r * rate, rgb_data.g * rate, rgb_data.b * rate)

    def generate_triangle(self,rgb_data):
        if(int(self.pattern_state) < (PATTERN_SPLIT / 2)):
            rate = (1.0 / (PATTERN_SPLIT / 2)) * self.pattern_state
        else:
            rate = ((-1.0 / (PATTERN_SPLIT / 2)) * self.pattern_state) + 1.0
        return RGBData(rgb_data.r * rate, rgb_data.g * rate, rgb_data.b * rate)

class OscDispatcher:
    def __init__(self,rgb_thread):
        self.rgb_thread = rgb_thread

    def color_mode(self,unused_addr,mode):
        self.rgb_thread.rgb_mode = mode
    
    def rgb(self,unused_addr,r,g,b):
        self.rgb_thread.rgb_color = RGBData(r,g,b)

    def rainbow_role_speed(self,unused_addr,speed):
        self.rgb_thread.rainbow_roll_skip = speed * DEF_ROLE_SPEED

    def pattern(self,unused_addr,pattern):
        self.rgb_thread.pattern_mode = pattern

    def bpm(self,unused_addr,bpm):
        self.rgb_thread.pattern_skip = PATTERN_SPLIT / bpm

    def luminosity(self,unused_addr,luminosity):
        self.rgb_thread.luminosity = luminosity

# Main program logic follows:
def main():
    # Create NeoPixel object with appropriate configuration.
    strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    # RGB Thread
    rgb_thread = RGBOutput(strip)

    # OSC 
    osc_dispacher = OscDispatcher(rgb_thread)
    dispatcher = Dispatcher()
    dispatcher.map('/color_mode', osc_dispacher.color_mode) # URLにコールバック関数を割り当てる
    dispatcher.map('/rgb', osc_dispacher.rgb) # URLにコールバック関数を割り当てる
    dispatcher.map('/rainbow_role_speed', osc_dispacher.rainbow_role_speed) # URLにコールバック関数を割り当てる
    dispatcher.map('/pattern', osc_dispacher.pattern) # URLにコールバック関数を割り当てる
    dispatcher.map('/bpm', osc_dispacher.bpm) # URLにコールバック関数を割り当てる
    dispatcher.map('/luminosity', osc_dispacher.luminosity) # URLにコールバック関数を割り当てる

    server = osc_server.ThreadingOSCUDPServer((IP, PORT), dispatcher)

    #Finish Initialization
    print ('Press Ctrl-C to quit.')

    #start server & thread
    rgb_thread.start()
    server.serve_forever()

if __name__ == '__main__':
    main()
