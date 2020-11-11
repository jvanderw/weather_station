# Copyright (c) 2020 Jess VanDerwalker

import time
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

TEMP_COLOR = 0xF3F7b7
MAIN_COLOR = 0x9000FF
SCROLL_DISPLAY = 0.03

# Current working directory
cwd = ("/" + __file__).rsplit("/", 1)[0]
FONT_12_PT = cwd + "/fonts/Arial-12.bdf"

class WeatherGraphics(displayio.Group):

    def __init__(self, display):
        super().__init__(max_size=3)
        self.display = display

        # Set up the different text groups
        self.root_group = displayio.Group(max_size=15)
        self.root_group.append(self)
        self.text_group = displayio.Group(max_size=5)
        self.append(self.text_group)
        self.description_group = displayio.Group(max_size=5)
        self.append(self.description_group)

        self.font_12_pt = bitmap_font.load_font(FONT_12_PT)
        glyphs = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: "
        self.font_12_pt.load_glyphs(glyphs)
        self.font_12_pt.load_glyphs("°")

        # Set the font and position of the tempature text
        self.temp_text = Label(self.font_12_pt, max_glyphs=6)
        self.temp_text.x = 2
        self.temp_text.y = 7
        self.temp_text.color = TEMP_COLOR
        self.temp_text.text = "-- °F"
        self.text_group.append(self.temp_text)

        # Place the description group
        self.description_text = Label(self.font_12_pt, max_glyphs=20)
        self.description_text.color = MAIN_COLOR
        self.description_text.text = "--"
        self.description_group.x = 2
        self.description_group.y = 23
        self.description_group.append(self.description_text)

        self.display.show(self.root_group);

    def display_weather(self, weather_json):
        """Display the weather based on data in passed in NOAA JSON blob"""
        temp = weather_json["properties"]["temperature"]["value"]
        # Convert to fahrenheit
        temp = (temp * (9/5)) + 32
        self.temp_text.text = "%s  °F" % round(temp)

        self.description_text.text = weather_json["properties"]["textDescription"]

        self.display.show(self.root_group)
        #self.scroll_description()

    def scroll_description(self):
        """Scroll the description as it may be longer than the display width"""
        self.description_group.x = self.display.width
        self.description_group.y = 23

        text_width = self.description_text.bounding_box[2]
        for _ in range(text_width + 1):
            self.description_group.x = self.description_group.x - 1
            time.sleep(SCROLL_DISPLAY)
