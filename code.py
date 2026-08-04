# Copyright (c) 2020-2026
#  Jess VanDerwalker
#

import time
import board
import traceback
from adafruit_matrixportal.network import Network
from adafruit_matrixportal.matrix import Matrix
import weather_graphics

print("Starting Weather Station")


def _log_stage(message):
    print("[stage]", message)


def _fatal_error(where, error):
    print("[fatal]", where, error)
    traceback.print_exception(type(error), error, error.__traceback__)


def _fetch_json(network_client, url, timeout=10):
    response = network_client.fetch(url, timeout=timeout)
    try:
        network_client.check_response(response)
        return response.json()
    finally:
        response.close()

try:
    from secrets import secrets
except ImportError:
    print("WiFi could not import secrets in secrets.py")
    raise

REQUIRED_SECRETS = ("station_id", "server_host", "server_port")
for required_key in REQUIRED_SECRETS:
    if required_key not in secrets:
        raise KeyError("Missing required secrets key: %s" % required_key)

location = secrets.get("location")
if not isinstance(location, (tuple, list)) or len(location) != 2:
    raise KeyError("Missing or invalid secrets key: location (latitude, longitude)")
location_lat = location[0]
location_lon = location[1]

HAS_AIO_CREDENTIALS = bool(secrets.get("aio_username")) and bool(secrets.get("aio_key"))
if not HAS_AIO_CREDENTIALS:
    print("AIO credentials not configured; skipping internet time sync.")

WEATHER_CURRENT = "http://%s:%s/%s" % (
    secrets["server_host"],
    secrets["server_port"],
    secrets["station_id"]
)
WEATHER_HEALTH = "http://%s:%s/health" % (
    secrets["server_host"],
    secrets["server_port"]
)
WEATHER_FORECAST = "http://%s:%s/forecast/%s,%s" % (
    secrets["server_host"],
    secrets["server_port"],
    location_lat,
    location_lon
)
WEATHER_DATA = []
SCROLL_PAUSE = 2

#Set up ESP32 WiFi
_log_stage("Initializing Network and Matrix")

try:
    matrix = Matrix()
    _log_stage("Matrix initialized")
    network = Network(status_neopixel=board.NEOPIXEL, debug=True)
    _log_stage("Network initialized")
    weather_gfx = weather_graphics.WeatherGraphics(matrix.display)
    _log_stage("Weather graphics initialized")
except Exception as e:
    _fatal_error("startup", e)
    raise

localtime_refresh = None
weather_refresh = None
weather_failures = 0
server_health_checked = False

print("Weather API endpoint:", WEATHER_CURRENT)
print("Forecast API endpoint:", WEATHER_FORECAST)

# Main update loop
while True:
    try:
        # Update the time every hour
        if HAS_AIO_CREDENTIALS and ((not localtime_refresh) or (time.monotonic() - localtime_refresh) > 3600):
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
                if not server_health_checked:
                    print("Checking weather_server health")
                    health_status = network.fetch_data(WEATHER_HEALTH, json_path=("status", ))
                    if health_status != "ok":
                        raise ValueError("weather_server health check returned '%s'" % health_status)
                    server_health_checked = True

                print("Retrieving data")
                response = _fetch_json(network, WEATHER_CURRENT)
                forecast_response = _fetch_json(network, WEATHER_FORECAST)

                periods = forecast_response.get("periods") if isinstance(forecast_response, dict) else None
                detailed_forecasts = []
                if isinstance(periods, list):
                    for period in periods[:3]:
                        if not isinstance(period, dict):
                            continue
                        detailed_forecast = period.get("detailedForecast") or period.get("detailedForcast")
                        if isinstance(detailed_forecast, str) and detailed_forecast:
                            detailed_forecasts.append(detailed_forecast)

                if detailed_forecasts:
                    summary_text = " ".join(detailed_forecasts)
                    existing_description = response.get("textDescription")
                    if isinstance(existing_description, str) and existing_description:
                        response["textDescription"] = "%s %s" % (existing_description, summary_text)
                    else:
                        response["textDescription"] = summary_text

                weather_gfx.display_weather(response)
                weather_refresh = time.monotonic()
                weather_failures = 0
            except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
                weather_failures = weather_failures + 1
                server_health_checked = False
                retry_delay = min(2 ** min(weather_failures, 8), 300)
                print("Failed to retrieve data, retrying in %s seconds\n" % retry_delay, e)
                time.sleep(retry_delay)
                continue

        weather_gfx.scroll_description()
        time.sleep(SCROLL_PAUSE)
    except Exception as e:
        _fatal_error("main loop", e)
        # Delay a bit to avoid rapid reset loops on persistent errors.
        time.sleep(5)