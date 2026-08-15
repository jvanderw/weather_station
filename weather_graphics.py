# Copyright (c) 2020-2026 Jess VanDerwalker

import time
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

TEMP_COLOR = 0xF3F7b7
MAIN_COLOR = 0x9000FF
SCROLL_SPEED = 0.03

# Current working directory
cwd = ("/" + __file__).rsplit("/", 1)[0]
FONT_12_PT = cwd + "/fonts/MatrixLight8x6.bdf"

class WeatherGraphics(displayio.Group):

    def __init__(self, display):
        super().__init__()
        self.display = display

        # Flags to track state of scrolling weather descriptions
        self.scroll_completed = False
        self.forecast_number = 0

        # The array of forecasts each with a name and detailedForecast
        self.forecasts = []

        # Set up the different text groups
        self.root_group = displayio.Group()
        self.root_group.append(self)
        self.current_group = displayio.Group()
        self.append(self.current_group)
        self.forecast_group = displayio.Group()
        self.append(self.forecast_group)

        self.font_12_pt = bitmap_font.load_font(FONT_12_PT)
        glyphs = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-.,:/'%() "
        self.font_12_pt.load_glyphs(glyphs)
        self.font_12_pt.load_glyphs("°")

        # Set the font and position of the tempature text
        self.temp_text = Label(self.font_12_pt)
        self.temp_text.x = 2
        self.temp_text.y = 7
        self.temp_text.color = TEMP_COLOR
        self.temp_text.text = "--°"
        self.current_group.append(self.temp_text)

        # Place the description group
        self.forecast_group.x = 2
        self.forecast_group.y = 23

        # Add the description text to the description group and preappend the name in a different colo
        self.name_text = Label(self.font_12_pt)
        self.name_text.x = 0
        self.name_text.color = TEMP_COLOR
        self.name_text.text = "--"
        self.forecast_group.append(self.name_text)

        self.description_text = Label(self.font_12_pt)
        self.description_text.x = self.name_text.bounding_box[2]
        self.description_text.color = MAIN_COLOR
        self.description_text.text = "--"
        self.forecast_group.append(self.description_text)

        self.display.root_group = self.root_group

    def display_weather(self, current_weather, detailed_forecasts):
        """Display weather based on flat JSON payload from weather_server"""
        temp = current_weather.get("temperature")
        if isinstance(temp, (int, float)):
            # Convert to fahrenheit
            temp = (temp * (9/5)) + 32
            self.temp_text.text = "%s°" % round(temp)
        else:
            self.temp_text.text = "--°"

        current_description = current_weather.get("textDescription")
        if isinstance(current_description, str) and current_description:
            self.forecasts = [dict(name="Current", detailedForecast=current_description)]

        for description in detailed_forecasts:
            name = description.get("name")
            detailed_forecast = description.get("detailedForecast")
            if isinstance(name, str) and isinstance(detailed_forecast, str) and name and detailed_forecast:
                self.forecasts.append(dict(name=name, detailedForecast=detailed_forecast))

    def scroll_single_description(self, ):
        """Scroll the description as it may be longer than the display width"""
        self.forecast_group.x = self.display.width
        self.forecast_group.y = 23

        self.name_text.text = "%s: " % self.forecasts[self.forecast_number].get("name")
        self.name_text.x = 0
        self.description_text.text = self.forecasts[self.forecast_number].get("detailedForecast")
        self.description_text.x = self.name_text.bounding_box[2]
        text_width = self.name_text.bounding_box[2] + self.description_text.bounding_box[2]
        for _ in range(text_width + self.display.width + 1):
            self.forecast_group.x = self.forecast_group.x - 1
            time.sleep(SCROLL_SPEED)

        # Increase the forecast number
        self.forecast_number = self.forecast_number + 1
        if self.forecast_number >= len(self.forecasts):
            self.forecast_number = 0