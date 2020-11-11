# Copyright (c) 2020 Jess VanDerwalker
#

import time
import board
import busio
from digitalio import DigitalInOut
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_requests as requests
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import neopixel
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
import weather_graphics

print("Starting Weather Station")

try:
    from secrets import secrets
except ImportError:
    print("WiFi could not import secrets in secrets.py")
    raise

WEATHER_CURRENT = "https://api.weather.gov/stations/%s/observations/latest" % (secrets["station_id"])
WEATHER_DATA = []
SCROLL_PAUSE = 2

#Set up ESP32 WiFi
print("Initializing Network and Matrix")

matrix = Matrix()
network = Network(status_neopixel=board.NEOPIXEL, debug=True)
weather_gfx = weather_graphics.WeatherGraphics(matrix.display)

localtime_refresh = None
weather_refresh = None

# Main update loop
while True:
    # Update the time every hour
    if (not localtime_refresh) or (time.monotonic() - localtime_refresh) > 3600:
        try:
            print("Getting time from internet!")
            network.get_local_time()
            localtime_refresh = time.monotonic()
        except RuntimeError as e:
            print("Some error occured, retrying! -", e)
            continue

    # Update the weather every 10 minutes
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        try:
            print("Retrieving data")
            response = network.fetch_data(WEATHER_CURRENT, json_path=(WEATHER_DATA, ))
            weather_gfx.display_weather(response)
            weather_refresh = time.monotonic()
        except (RuntimeError) as e:
            print("Failed to retrieve data, retrying\n", e)
            continue

    weather_gfx.scroll_description()
    time.sleep(SCROLL_PAUSE)
