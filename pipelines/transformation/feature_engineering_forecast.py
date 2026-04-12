"""
pipelines/transformation/feature_engineering_forecast.py
─────────────────────────────────────────────────────────
Joins weather_forecast.json + pollution_forecast.json on date,
derives ALL health features used in model training (including the
new v2 max/min-derived features), and writes forecast_features.csv.

New in v2: computes temp_range, heat_stress_peak, dust_risk_index,
rain_wash_effect to match the enriched training feature set.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

from utils.logger import get_logger

log = get_logger("feature_engineering_forecast")

WEATHER_PATH   = os.path.join(ROOT, "data", "raw", "weather_forecast.json")
POLLUTION_PATH = os.path.join(ROOT, "data", "raw", "pollution_forecast.json")
OUT_PATH       = os.path.join(ROOT, "data", "processed", "forecast_features.csv")


def load_json(path: str, label: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{label} file not found: {path}\n"
            "Run the corresponding fetch script first."
        )
    with open(path) as f:
        data = json.load(f)
    df = pd.DataFrame(data["days"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    log.info("Loaded %s: %d rows", label, len(df))
    return df


def engineer(weather: pd.DataFrame, pollution: pd.DataFrame) -> pd.DataFrame:
    df = pd.merge(weather, pollution, on=["date", "horizon"], how="inner")

    if df.empty:
        raise ValueError(
            "Inner join on [date, horizon] produced 0 rows. "
            "Check that both forecast files cover the same 3 days."
        )

    # Fill nulls with Cairo baseline values
    baseline = {
        "pm25"             : 35.0,
        "pm10"             : 55.0,
        "aqi"              : 90.0,
        "ozone"            : 60.0,
        "nitrogen_dioxide" : 25.0,
        "sulphur_dioxide"  : 5.0,
        "temp_max"         : df["temperature"].max() if "temperature" in df.columns else 35.0,
        "temp_min"         : df["temperature"].min() if "temperature" in df.columns else 18.0,
        "humidity_min"     : 30.0,
        "humidity_max"     : df["humidity"].max() if "humidity" in df.columns else 60.0,
        "wind_max"         : df["wind"].max() if "wind" in df.columns else 20.0,
        "wind_gust_max"    : 25.0,
        "apparent_temp_max": 38.0,
        "precipitation"    : 0.0,
    }
    for col, val in baseline.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)
        else:
            df[col] = val

    def c(name):
        return df[name] if name in df.columns else 0

    # ── Original features ──────────────────────────────────────────────────
    df["heat_index"] = (
        c("temperature") + (0.33 * c("humidity")) - (0.70 * c("wind"))
    )
    df["pollution_level"] = (
        (c("pm25") * 0.5) + (c("pm10") * 0.3) + (c("aqi") * 0.2)
    )
    df["respiratory_stress"] = (
        (c("pm25") * 0.4) + (c("ozone") * 0.3) +
        (c("nitrogen_dioxide") * 0.2) + (c("sulphur_dioxide") * 0.1)
    )
    df["uv_risk"] = 0.0     # UV not available in free OWM forecast tier

    # ── New v2 features ────────────────────────────────────────────────────
    df["temp_range"] = c("temp_max") - c("temp_min")

    df["heat_stress_peak"] = c("apparent_temp_max")

    df["dust_risk_index"] = c("wind_max") * (1 - c("humidity_min") / 100)

    df["rain_wash_effect"] = c("precipitation").clip(0, 20)

    df["processed_at"] = datetime.now(timezone.utc).isoformat()

    # Column order must match FEATURE_COLS in predict_forecast.py
    cols = [
        "date", "horizon",
        # Core means
        "temperature", "humidity", "wind", "pressure", "cloud_cover",
        # Pollution
        "pm25", "pm10", "aqi", "ozone", "nitrogen_dioxide", "sulphur_dioxide",
        # Original derived
        "heat_index", "pollution_level", "respiratory_stress", "uv_risk",
        # New v2
        "temp_range", "heat_stress_peak", "dust_risk_index", "rain_wash_effect",
        "processed_at",
    ]
    df = df[[c for c in cols if c in df.columns]]

    log.info("Engineered features for %d forecast days", len(df))
    for _, row in df.iterrows():
        log.info(
            "  Day +%d (%s) → heat_index=%.1f  dust_risk=%.1f  "
            "pollution_level=%.1f  rain_wash=%.1f",
            row["horizon"], row["date"],
            row["heat_index"], row["dust_risk_index"],
            row["pollution_level"], row["rain_wash_effect"],
        )
    return df


def save(df: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    log.info("Saved forecast features → %s", OUT_PATH)


if __name__ == "__main__":
    weather   = load_json(WEATHER_PATH,   "weather forecast")
    pollution = load_json(POLLUTION_PATH, "pollution forecast")
    features  = engineer(weather, pollution)
    save(features)