"""
pipelines/ingestion/fetch_pollution_forecast.py
───────────────────────────────────────────────
Uses OpenWeatherMap's Air Pollution Forecast endpoint (free tier).
Aggregates hourly slots → daily means for the next 3 days.

AQI is calculated from PM2.5 using real EPA breakpoints instead of
OWM's coarse 1-5 scale which was mapping everything to AQI 125.

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


def pm25_to_us_aqi(pm25: float) -> int:
    """
    Convert PM2.5 (μg/m³) to US AQI using official EPA linear interpolation.
    This replaces the old OWM 1-5 scale mapping which forced AQI=125 for
    everything at level 3 — causing all forecast days to predict Avoid Outdoors.

EPA breakpoints:
    0.0  – 12.0   → AQI   0 – 50   (Good)
    12.1 – 35.4   → AQI  51 – 100  (Moderate)
    35.5 – 55.4   → AQI 101 – 150  (Unhealthy for sensitive groups)
    55.5 – 150.4  → AQI 151 – 200  (Unhealthy)
    150.5 – 250.4 → AQI 201 – 300  (Very unhealthy)
    250.5 – 350.4 → AQI 301 – 400  (Hazardous)
    350.5 – 500.4 → AQI 401 – 500  (Hazardous)
"""
    breakpoints = [
        (0.0,   12.0,   0,   50),
        (12.1,  35.4,  51,  100),
        (35.5,  55.4, 101,  150),
        (55.5, 150.4, 151,  200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if bp_lo <= pm25 <= bp_hi:
            aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo
            return round(aqi)
    return 500


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
        })

    daily = []
    for date_str in sorted(buckets):
        slots = buckets[date_str]
        n     = len(slots)

        def avg(key):
            vals = [s[key] for s in slots if s[key] is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        pm25_avg = avg("pm25")

        # Compute real US AQI directly from PM2.5 using EPA formula
        # Old approach: OWM_AQI_MAP.get(round(owm_aqi_mean), 125)
        # That was returning 125 for everything at OWM level 3 regardless
        # of actual PM2.5 value — now fixed with proper EPA interpolation
        us_aqi = pm25_to_us_aqi(pm25_avg) if pm25_avg is not None else 90

        record = {
            "date"             : date_str,
            "horizon"          : (datetime.fromisoformat(date_str).date() - today).days,
            "pm25"             : pm25_avg,
            "pm10"             : avg("pm10"),
            "aqi"              : us_aqi,
            "ozone"            : avg("ozone"),
            "nitrogen_dioxide" : avg("nitrogen_dioxide"),
            "sulphur_dioxide"  : avg("sulphur_dioxide"),
            "source"           : "openweathermap_air_pollution_forecast",
        }
        daily.append(record)
        log.info(
            "Day +%d (%s): pm25=%.1f → aqi=%d  no2=%.1f",
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