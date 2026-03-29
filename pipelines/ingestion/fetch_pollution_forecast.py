"""
pipelines/ingestion/fetch_pollution_forecast.py
───────────────────────────────────────────────
Uses OpenWeatherMap's Air Pollution Forecast endpoint (free tier).
Aggregates hourly slots → daily means for the next 3 days.

Output: data/raw/pollution_forecast.json
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

log = get_logger("fetch_pollution_forecast")

API_KEY  = os.environ["OPENWEATHER_API_KEY"]
LAT, LON = 30.0626, 31.2497
URL      = (
    "https://api.openweathermap.org/data/2.5/air_pollution/forecast"
    f"?lat={LAT}&lon={LON}&appid={API_KEY}"
)
OUT_PATH = os.path.join(ROOT, "data", "raw", "pollution_forecast.json")

# AQI breakpoints: OWM uses a 1-5 scale → convert to US AQI approximation
OWM_AQI_MAP = {1: 25, 2: 75, 3: 125, 4: 200, 5: 300}


def fetch() -> dict:
    log.info("Fetching air pollution forecast from OpenWeatherMap …")
    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    log.info("Received %d hourly pollution slots", len(raw.get("list", [])))
    return raw


def aggregate_to_daily(raw: dict) -> list[dict]:
    today   = datetime.now(timezone.utc).date()
    buckets: dict[str, list] = defaultdict(list)

    for slot in raw.get("list", []):
        dt      = datetime.fromtimestamp(slot["dt"], tz=timezone.utc)
        day     = dt.date()
        horizon = (day - today).days

        if horizon < 1 or horizon > 3:
            continue

        comp = slot.get("components", {})
        buckets[str(day)].append({
            "pm25"             : comp.get("pm2_5", None),
            "pm10"             : comp.get("pm10",  None),
            "ozone"            : comp.get("o3",    None),
            "nitrogen_dioxide" : comp.get("no2",   None),
            "sulphur_dioxide"  : comp.get("so2",   None),
            "owm_aqi"          : slot.get("main", {}).get("aqi", 3),
        })

    daily = []
    for date_str in sorted(buckets):
        slots = buckets[date_str]
        n     = len(slots)

        def avg(key):
            vals = [s[key] for s in slots if s[key] is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        owm_aqi_mean = sum(s["owm_aqi"] for s in slots) / n
        us_aqi_approx = OWM_AQI_MAP.get(round(owm_aqi_mean), 125)

        record = {
            "date"             : date_str,
            "horizon"          : (datetime.fromisoformat(date_str).date() - today).days,
            "pm25"             : avg("pm25"),
            "pm10"             : avg("pm10"),
            "aqi"              : us_aqi_approx,
            "ozone"            : avg("ozone"),
            "nitrogen_dioxide" : avg("nitrogen_dioxide"),
            "sulphur_dioxide"  : avg("sulphur_dioxide"),
            "source"           : "openweathermap_air_pollution_forecast",
        }
        daily.append(record)
        log.info(
            "Day +%d (%s): pm25=%.1f  aqi=%d  no2=%.1f",
            record["horizon"], date_str,
            record["pm25"] or 0, record["aqi"], record["nitrogen_dioxide"] or 0,
        )

    if not daily:
        raise ValueError("No pollution forecast data found for horizons 1–3")

    return daily


def save(daily: list[dict]) -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    payload = {
        "fetched_at" : datetime.now(timezone.utc).isoformat(),
        "days"       : daily,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    log.info("Saved pollution forecast → %s", OUT_PATH)


if __name__ == "__main__":
    raw   = fetch()
    daily = aggregate_to_daily(raw)
    save(daily)