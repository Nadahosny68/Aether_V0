"""
pipelines/ingestion/fetch_weather_forecast.py
─────────────────────────────────────────────
Pulls the OpenWeatherMap 5-day / 3-hour forecast for Cairo and
aggregates to daily means for the next 3 days.

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
LAT, LON = 30.0626, 31.2497          # Cairo centre
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
    Returns a list of dicts sorted by date ascending.
    """
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, list] = defaultdict(list)

    for slot in raw.get("list", []):
        dt   = datetime.fromtimestamp(slot["dt"], tz=timezone.utc)
        day  = dt.date()

        horizon = (day - today).days
        if horizon < 1 or horizon > 3:
            continue

        buckets[str(day)].append({
            "temperature" : slot["main"]["temp"],
            "humidity"    : slot["main"]["humidity"],
            "wind"        : slot["wind"]["speed"] * 3.6,   # m/s → km/h
            "pressure"    : slot["main"]["pressure"],
            "cloud_cover" : slot["clouds"]["all"],
        })

    daily = []
    for date_str in sorted(buckets):
        slots  = buckets[date_str]
        n      = len(slots)
        record = {
            "date"        : date_str,
            "horizon"     : (datetime.fromisoformat(date_str).date() - today).days,
            "temperature" : round(sum(s["temperature"] for s in slots) / n, 4),
            "humidity"    : round(sum(s["humidity"]    for s in slots) / n, 4),
            "wind"        : round(sum(s["wind"]        for s in slots) / n, 4),
            "pressure"    : round(sum(s["pressure"]    for s in slots) / n, 4),
            "cloud_cover" : round(sum(s["cloud_cover"] for s in slots) / n, 4),
            "source"      : "openweathermap_forecast",
        }
        daily.append(record)
        log.info(
            "Day +%d (%s): temp=%.1f°C  hum=%.0f%%  wind=%.1f km/h",
            record["horizon"], date_str,
            record["temperature"], record["humidity"], record["wind"],
        )

    if not daily:
        raise ValueError("No forecast data found for horizons 1–3")

    return daily


def save(daily: list[dict]) -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    payload = {
        "fetched_at" : datetime.now(timezone.utc).isoformat(),
        "days"       : daily,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    log.info("Saved weather forecast → %s", OUT_PATH)


if __name__ == "__main__":
    raw   = fetch()
    daily = aggregate_to_daily(raw)
    save(daily)