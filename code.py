# Copyright (c) 2020-2026
#  Jess VanDerwalker
#
import gc
import time
import board
import traceback
from adafruit_matrixportal.matrix import Matrix
import network_utils as _network_utils



def _log_info(message):
    print("[info]", message)

def _log_stage(message):
    print("[stage]", message)


def _fatal_error(where, error):
    print("[fatal]", where, error)
    traceback.print_exception(type(error), error, error.__traceback__)




def _fetch_json(network_client: Network, url: str, timeout=10) -> dict:
    response = None
    try:
        response = network_client.fetch(url, timeout=timeout)
        network_client.check_response(response)
        return response.json()
    except RuntimeError as exc:
        global _network_utils

        # Lazy-import helper in case top-level import failed during startup.
        if _network_utils is None:
            try:
                import network_utils as _loaded_network_utils

                _network_utils = _loaded_network_utils
            except Exception:
                _network_utils = None

        if _network_utils is not None:
            try:
                if _network_utils.should_retry_with_socket_reset(exc):
                    print("[warn] Resetting network sockets after stale socket error")
                    _network_utils.reset_connection_manager()
            except Exception as helper_exc:
                print("[warn] Socket reset helper failed:", helper_exc)
        raise
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _sleep_with_scroll(weather_display, delay_seconds):
    remaining = delay_seconds
    while remaining > 0:
        weather_display.scroll_description()
        interval = 1 if remaining > 1 else remaining
        time.sleep(interval)
        remaining = remaining - interval

_log_info("Starting Weather Station")

try:
    from secrets import secrets
except ImportError:
    _fatal_error("startup", ImportError("WiFi could not import secrets in secrets.py"))
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
    _log_info("AIO credentials not configured; skipping internet time sync.")

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

gc.collect()
try:
    matrix = Matrix()
except MemoryError as e:
    _log_info("MemoryError during initialization, attempting to free memory and retry")
    gc.collect()
    matrix = Matrix(bit_depth=1 )
except Exception as e:
    _fatal_error("startup", e)
    raise
_log_stage("Matrix initialized")

from adafruit_matrixportal.network import Network
import weather_graphics

_log_stage("Initializing Network and Matrix")
network: Network = Network(status_neopixel=board.NEOPIXEL, debug=True)
_log_stage("Network initialized")
weather_gfx = weather_graphics.WeatherGraphics(matrix.display)
_log_stage("Weather graphics initialized")

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
                    health_payload = _fetch_json(network, WEATHER_HEALTH)
                    health_status = health_payload.get("status")
                    if health_status != "ok":
                        raise ValueError("weather_server health check returned '%s'" % health_status)
                    server_health_checked = True

                print("Retrieving data")
                current_response = _fetch_json(network, WEATHER_CURRENT)
                forecast_response = _fetch_json(network, WEATHER_FORECAST)

                periods = forecast_response.get("periods") if isinstance(forecast_response, dict) else None
                detailed_forecasts = []
                if isinstance(periods, list):
                    for period in periods:
                        if not isinstance(period, dict):
                            continue
                        detailed_forecast = period.get("detailedForecast")
                        name = period.get("name")
                        if isinstance(name, str) and name:
                            if isinstance(detailed_forecast, str) and detailed_forecast:
                                detailed_forecast = detailed_forecast.replace("\n", " ").replace("\r", " ").replace("\t", " ")
                                detailed_forecasts.append(dict(name=name, detailedForecast=detailed_forecast))

                if detailed_forecasts:
                    current_description = current_response.get("textDescription")
                    if isinstance(current_description, str) and current_description:
                        detailed_forecasts.insert(0, dict(name="Current", detailedForecast=current_description))
                    else:
                        detailed_forecasts.insert(0, dict(name="Current", detailedForecast="No description"))

                weather_gfx.display_weather(current_response, detailed_forecasts)
                weather_refresh = time.monotonic()
                weather_failures = 0
            except (RuntimeError, ValueError, TypeError, KeyError, OSError) as e:
                weather_failures = weather_failures + 1
                server_health_checked = False
                retry_delay = min(2 ** min(weather_failures, 8), 300)
                print("Failed to retrieve data, retrying in %s seconds\n" % retry_delay, e)
                _sleep_with_scroll(weather_gfx, retry_delay)
                continue

        weather_gfx.scroll_single_description()
        time.sleep(SCROLL_PAUSE)
    except Exception as e:
        _fatal_error("main loop", e)
        # Delay a bit to avoid rapid reset loops on persistent errors.
        time.sleep(5)