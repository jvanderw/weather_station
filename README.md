# weather_station

CircuitPython app for Matrix Portal M4 (32x64 RGB matrix) that reads weather data from weather_server on your local network and displays temperature plus scrolling description.

## Hardware target

- Adafruit Matrix Portal M4
- 64x32 RGB LED matrix

## What it does

- Connects to local Wi-Fi
- Syncs local time periodically
- Calls weather_server over LAN
- Verifies weather_server health endpoint before weather fetch
- Displays temperature (Fahrenheit) and scrolling text description
- Retries failed fetches with bounded exponential backoff

## Required secrets

Create or update secrets.py on the board storage with:

secrets = {
    "ssid": "YOUR_WIFI_SSID",
    "password": "YOUR_WIFI_PASSWORD",
    "station_id": "KPDX",
    "server_host": "192.168.1.50",
    "server_port": 3030
}

Notes:

- server_host should be the LAN IP where weather_server is running.
- station_id is passed through to weather_server route GET /:stationId.

## Server contract expected

weather_station expects a flat JSON response from weather_server:

{
  "station": "https://api.weather.gov/stations/KPDX",
  "temperature": 19.4,
  "relativeHumidity": 62,
  "textDescription": "Mostly Cloudy"
}

Fields used by display logic:

- temperature
- textDescription

## Runtime behavior

- Time refresh: every 60 minutes
- Weather refresh: every 10 minutes
- Scroll pause: 2 seconds between cycles
- Failure backoff: exponential, capped at 300 seconds

## Run order for full system

1. Start weather_server first on LAN host.
2. Confirm health endpoint works:
   - http://<server_host>:3030/health
3. Boot Matrix Portal with updated secrets.py.
4. Watch serial logs for:
   - Wi-Fi connection
   - health check success
   - weather fetch success

## Launching the application

1. Make sure weather_server is already running on the local network.
2. Update secrets.py on the board with ssid, password, station_id, server_host, and server_port.
3. Copy the project to the CIRCUITPY drive.
4. Reset or power-cycle the Matrix Portal M4.
5. Confirm the display shows temperature and a scrolling weather description.

Useful local checks:

- If the board logs a health check failure, verify server_host and server_port.
- If the display stays blank, confirm the serial console shows a successful fetch and that weather_server returns a flat JSON payload.

## Troubleshooting

- Missing secrets key:
  - App raises KeyError at startup with the missing key name.
- Health check fails:
  - Confirm server_host/server_port, LAN connectivity, and weather_server process.
- Fetch failures:
  - App retries automatically with backoff.
- Display fallback values:
  - If payload is missing temperature or textDescription, display shows defaults instead of crashing.

## Development notes

- This repository includes CircuitPython libraries under lib for on-device execution.
- Do not commit desktop Python virtual environments; keep reproducible dependency notes instead.
