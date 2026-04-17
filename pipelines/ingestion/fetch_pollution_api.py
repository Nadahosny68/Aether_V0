"""
pipelines/ingestion/fetch_pollution_api.py
───────────────────────────────────────────
Fetches today's air pollution data from OpenWeatherMap Air Pollution API.
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from utils.logger import get_logger
log = get_logger("fetch_pollution_api")

API_KEY  = os.environ["OPENWEATHER_API_KEY"]
LAT, LON = 30.0626, 31.2497

URL = (
    "https://api.openweathermap.org/data/2.5/air_pollution"
    f"?lat={LAT}&lon={LON}&appid={API_KEY}"
)

RAW_DIR = os.path.join(ROOT, "data", "raw")

# ✅ Cairo timezone
cairo_tz = timezone(timedelta(hours=2))


def pm25_to_us_aqi(pm25: float) -> int:
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
            return round(((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (pm25 - bp_lo) + aqi_lo)
    return 500


def fetch() -> dict:
    log.info("Fetching current air pollution from OpenWeatherMap …")

    resp = requests.get(URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not data.get("list"):
        raise ValueError("OWM air pollution API returned empty list")

    slot = data["list"][0]
    comp = slot.get("components", {})

    pm25 = comp.get("pm2_5")
    aqi  = pm25_to_us_aqi(pm25) if pm25 is not None else None

    # ✅ Time handling
    now_utc   = datetime.now(timezone.utc)
    now_cairo = datetime.now(cairo_tz)

    record = {
        "fetched_at"        : now_utc.isoformat(),   # keep UTC for tracking
        "date"              : now_cairo.strftime("%Y-%m-%d"),  # ✅ Cairo date
        "source"            : "openweathermap_air_pollution",

        "aqi"               : aqi,
        "pm25"              : pm25,
        "pm10"              : comp.get("pm10"),
        "ozone"             : comp.get("o3"),
        "nitrogen_dioxide"  : comp.get("no2"),
        "sulphur_dioxide"   : comp.get("so2"),
        "carbon_monoxide"   : comp.get("co"),

        "owm_aqi_index"     : slot.get("main", {}).get("aqi"),

        "european_aqi"      : None,
        "dust"              : None,
        "aerosol_optical_depth": None,
        "uv_index"          : None,
    }

    log.info(
        "Pollution: AQI=%s  PM2.5=%.1f  PM10=%.1f  NO2=%.1f  O3=%.1f  CO=%.0f  SO2=%.1f",
        record["aqi"],
        record["pm25"]             or 0,
        record["pm10"]             or 0,
        record["nitrogen_dioxide"] or 0,
        record["ozone"]            or 0,
        record["carbon_monoxide"]  or 0,
        record["sulphur_dioxide"]  or 0,
    )

    return record


def save(record: dict) -> str:
    os.makedirs(RAW_DIR, exist_ok=True)

    # ✅ Cairo-based filename
    now_cairo = datetime.now(cairo_tz)
    today_str = now_cairo.strftime("%Y%m%d")

    filename = f"pollution_api_{today_str}.json"
    filepath = os.path.join(RAW_DIR, filename)

    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)

    log.info("Saved pollution data → %s", filepath)
    return filepath


if __name__ == "__main__":
    record = fetch()
    save(record)