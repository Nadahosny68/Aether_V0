"""
pipelines/ingestion/fetch_weather_api.py
─────────────────────────────────────────
Fetches today's weather from OpenWeatherMap.
Uses TWO endpoints:
  1. /weather  → current conditions (temp, humidity, wind, pressure)
  2. /forecast → today's slots to compute daily max/min/apparent_max

This gives append_daily_api_row.py enough data to fill all
EnvironmentalFeatures columns without NULLs.

Output: data/raw/weather_api_YYYYMMDD.json
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, date
from collections import defaultdict
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from utils.logger import get_logger
log = get_logger("fetch_weather_api")

API_KEY  = os.environ["OPENWEATHER_API_KEY"]
LAT, LON = 30.0626, 31.2497

CURRENT_URL  = (
    f"https://api.openweathermap.org/data/2.5/weather"
    f"?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
)
FORECAST_URL = (
    f"https://api.openweathermap.org/data/2.5/forecast"
    f"?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric&cnt=8"  # next 24h = 8 slots of 3h
)

RAW_DIR = os.path.join(ROOT, "data", "raw")


def fetch_current() -> dict:
    log.info("Fetching current weather …")
    resp = requests.get(CURRENT_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    record = {
        "temperature" : data["main"]["temp"],
        "humidity"    : data["main"]["humidity"],
        "wind"        : round(data["wind"]["speed"] * 3.6, 4),   # m/s → km/h
        "pressure"    : data["main"]["pressure"],
        "cloud_cover" : data["clouds"]["all"],
    }
    log.info("Current: temp=%.1f°C  hum=%.0f%%  wind=%.1f km/h",
            record["temperature"], record["humidity"], record["wind"])
    return record


def fetch_today_stats() -> dict:
    """
    Pull the next 24h forecast slots and extract today's daily stats.
    OWM /forecast gives 3-hour slots — we take all slots for today
    and compute max/min/apparent_max.
    """
    log.info("Fetching today's forecast slots for daily stats …")
    resp = requests.get(FORECAST_URL, timeout=15)
    resp.raise_for_status()
    raw  = resp.json()

    today    = date.today()
    slots_today = []

    for slot in raw.get("list", []):
        dt  = datetime.fromtimestamp(slot["dt"], tz=timezone.utc)
        if dt.date() == today:
            wind_speed = slot["wind"]["speed"] * 3.6
            wind_gust  = slot["wind"].get("gust", slot["wind"]["speed"]) * 3.6
            slots_today.append({
                "temp"     : slot["main"]["temp"],
                "temp_max" : slot["main"].get("temp_max", slot["main"]["temp"]),
                "temp_min" : slot["main"].get("temp_min", slot["main"]["temp"]),
                "humidity" : slot["main"]["humidity"],
                "feels"    : slot["main"].get("feels_like", slot["main"]["temp"]),
                "wind"     : wind_speed,
                "gust"     : wind_gust,
                "rain_3h"  : slot.get("rain", {}).get("3h", 0.0),
            })

    if not slots_today:
        log.warning("No forecast slots found for today — daily stats will be estimated")
        return {}

    stats = {
        "temp_max"          : round(max(s["temp_max"] for s in slots_today), 4),
        "temp_min"          : round(min(s["temp_min"] for s in slots_today), 4),
        "humidity_max"      : round(max(s["humidity"] for s in slots_today), 4),
        "humidity_min"      : round(min(s["humidity"] for s in slots_today), 4),
        "wind_max"          : round(max(s["wind"]     for s in slots_today), 4),
        "wind_gust_max"     : round(max(s["gust"]     for s in slots_today), 4),
        "apparent_temp_max" : round(max(s["feels"]    for s in slots_today), 4),
        "apparent_temp_min" : round(min(s["feels"]    for s in slots_today), 4),
        "apparent_temp_mean": round(
            sum(s["feels"] for s in slots_today) / len(slots_today), 4
        ),
        "precipitation"     : round(sum(s["rain_3h"]  for s in slots_today), 4),
    }
    log.info(
        "Today stats: temp %.1f–%.1f°C  wind_max=%.1f  hum_min=%.0f%%  rain=%.1fmm",
        stats["temp_min"], stats["temp_max"],
        stats["wind_max"], stats["humidity_min"], stats["precipitation"],
    )
    return stats


def save(record: dict) -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename  = f"weather_api_{today_str}.json"
    filepath  = os.path.join(RAW_DIR, filename)

    record["fetched_at"] = datetime.now(timezone.utc).isoformat()
    record["date"]       = str(date.today())

    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)
    log.info("Saved weather → %s", filepath)
    return filepath


if __name__ == "__main__":
    current = fetch_current()
    stats   = fetch_today_stats()
    record  = {**current, **stats}  # merge both dicts
    save(record)