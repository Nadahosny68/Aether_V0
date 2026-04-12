"""
pipelines/ingestion/fetch_weather_forecast.py
─────────────────────────────────────────────
Pulls the OpenWeatherMap 5-day / 3-hour forecast for Cairo and
aggregates to daily stats for the next 3 days.

New in v2: extracts max/min/range from 3-hour slots so the forecast
features match the richer feature set used in model training.

Output: data/raw/weather_forecast.json
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

from utils.logger import get_logger

log = get_logger("fetch_weather_forecast")

API_KEY  = os.environ["OPENWEATHER_API_KEY"]
LAT, LON = 30.0626, 31.2497
URL      = (
    "https://api.openweathermap.org/data/2.5/forecast"
    f"?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&cnt=24"
)
OUT_PATH = os.path.join(ROOT, "data", "raw", "weather_forecast.json")


def fetch() -> dict:
    log.info("Fetching weather forecast from OpenWeatherMap …")
    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    log.info("Received %d forecast slots", len(raw.get("list", [])))
    return raw


def aggregate_to_daily(raw: dict) -> list[dict]:
    """
    Collapse 3-hour slots → daily aggregates for the next 3 calendar days.

    Each slot from OWM provides:
    main.temp        → instantaneous temperature
    main.temp_max    → max in this 3h window
    main.temp_min    → min in this 3h window
    main.humidity    → instantaneous humidity
    main.pressure    → instantaneous pressure
    wind.speed       → instantaneous wind speed
    wind.gust        → wind gust (if present)
    clouds.all       → cloud cover %
    rain.3h          → rain in this 3h window (if present)

We compute:
    temperature  = mean of all slot temps (daily mean)
    temp_max     = max of all slot temp_max  (daily peak)
    temp_min     = min of all slot temp_min  (daily lowest)
    humidity     = mean of all slot humidity
    humidity_max = max of all slot humidity
    humidity_min = min of all slot humidity
    wind         = mean wind speed (km/h)
    wind_max     = max wind speed across slots (km/h)
    wind_gust_max= max gust across slots (km/h)
    pressure     = mean pressure
    cloud_cover  = mean cloud cover
    precipitation= sum of rain.3h across all slots
    apparent_temp_max = estimated from temp_max (OWM doesn't provide directly)
"""
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, list] = defaultdict(list)

    for slot in raw.get("list", []):
        dt      = datetime.fromtimestamp(slot["dt"], tz=timezone.utc)
        day     = dt.date()
        horizon = (day - today).days

        if horizon < 1 or horizon > 3:
            continue

        wind_speed = slot["wind"]["speed"] * 3.6       # m/s → km/h
        wind_gust  = slot["wind"].get("gust", slot["wind"]["speed"]) * 3.6
        rain_3h    = slot.get("rain", {}).get("3h", 0.0)

        buckets[str(day)].append({
            "temp"      : slot["main"]["temp"],
            "temp_max"  : slot["main"].get("temp_max", slot["main"]["temp"]),
            "temp_min"  : slot["main"].get("temp_min", slot["main"]["temp"]),
            "humidity"  : slot["main"]["humidity"],
            "pressure"  : slot["main"]["pressure"],
            "wind"      : wind_speed,
            "wind_gust" : wind_gust,
            "cloud"     : slot["clouds"]["all"],
            "rain_3h"   : rain_3h,
        })

    daily = []
    for date_str in sorted(buckets):
        slots  = buckets[date_str]
        n      = len(slots)

        temp_mean    = round(sum(s["temp"]      for s in slots) / n, 4)
        temp_max     = round(max(s["temp_max"]  for s in slots), 4)
        temp_min     = round(min(s["temp_min"]  for s in slots), 4)
        hum_mean     = round(sum(s["humidity"]  for s in slots) / n, 4)
        hum_max      = round(max(s["humidity"]  for s in slots), 4)
        hum_min      = round(min(s["humidity"]  for s in slots), 4)
        wind_mean    = round(sum(s["wind"]      for s in slots) / n, 4)
        wind_max     = round(max(s["wind"]      for s in slots), 4)
        wind_gust_max= round(max(s["wind_gust"] for s in slots), 4)
        pressure     = round(sum(s["pressure"]  for s in slots) / n, 4)
        cloud        = round(sum(s["cloud"]     for s in slots) / n, 4)
        precip       = round(sum(s["rain_3h"]   for s in slots), 4)

        # Apparent temperature max — OWM doesn't provide this directly
        # Estimate using heat index formula at peak conditions
        apparent_temp_max = round(temp_max + (0.33 * hum_max) - (0.70 * wind_mean), 4)

        record = {
            "date"             : date_str,
            "horizon"          : (datetime.fromisoformat(date_str).date() - today).days,
            # Means (same as before)
            "temperature"      : temp_mean,
            "humidity"         : hum_mean,
            "wind"             : wind_mean,
            "pressure"         : pressure,
            "cloud_cover"      : cloud,
            # NEW: max/min/extremes
            "temp_max"         : temp_max,
            "temp_min"         : temp_min,
            "humidity_max"     : hum_max,
            "humidity_min"     : hum_min,
            "wind_max"         : wind_max,
            "wind_gust_max"    : wind_gust_max,
            "apparent_temp_max": apparent_temp_max,
            "precipitation"    : precip,
            "source"           : "openweathermap_forecast",
        }
        daily.append(record)
        log.info(
            "Day +%d (%s): temp=%.1f°C (%.1f–%.1f)  wind_max=%.1f  hum_min=%.0f%%  rain=%.1fmm",
            record["horizon"], date_str,
            temp_mean, temp_min, temp_max,
            wind_max, hum_min, precip,
        )

    if not daily:
        raise ValueError("No forecast data found for horizons 1–3")

    return daily


from datetime import datetime, timezone

def save(daily: list[dict]) -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    # ✅ 1. Save daily versioned file (used by pipeline)
    daily_file = os.path.join(ROOT, "data", "raw", f"weather_api_{today_str}.json")

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "days": daily,
    }

    with open(daily_file, "w") as f:
        json.dump(payload, f, indent=2)

    log.info("Saved DAILY weather file → %s", daily_file)

    # ✅ 2. (Optional) keep latest snapshot
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)

    log.info("Updated latest weather snapshot → %s", OUT_PATH)


if __name__ == "__main__":
    raw   = fetch()
    daily = aggregate_to_daily(raw)
    save(daily)