"""
pipelines/transformation/feature_engineering_forecast.py
─────────────────────────────────────────────────────────
Joins weather_forecast.json + pollution_forecast.json on date,
derives the same 5 composite health features used in training,
and writes data/processed/forecast_features.csv

Usage:
    python pipelines/transformation/feature_engineering_forecast.py
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

WEATHER_PATH    = os.path.join(ROOT, "data", "raw", "weather_forecast.json")
POLLUTION_PATH  = os.path.join(ROOT, "data", "raw", "pollution_forecast.json")
OUT_PATH        = os.path.join(ROOT, "data", "processed", "forecast_features.csv")


# ── Same feature functions as feature_engineering.py ──────────────────────────

def compute_heat_index(temp, humidity, wind):
    return temp + (0.33 * humidity) - (0.70 * wind)


def compute_pollution_level(pm25, pm10, aqi):
    return (pm25 * 0.5) + (pm10 * 0.3) + (aqi * 0.2)


def compute_respiratory_stress(pm25, ozone, no2, so2):
    return (pm25 * 0.4) + (ozone * 0.3) + (no2 * 0.2) + (so2 * 0.1)


def compute_uv_risk(uv_index=0.0):
    """UV forecast not in free OWM tier — default 0; override if source added."""
    return float(np.clip((uv_index / 11) * 100, 0, 100))


# ── Load + join ────────────────────────────────────────────────────────────────

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

    # Fill any nulls with conservative Cairo baseline values
    # (avoids NaN propagation into the model)
    baseline = {
        "pm25"             : 35.0,
        "pm10"             : 55.0,
        "aqi"              : 90.0,
        "ozone"            : 60.0,
        "nitrogen_dioxide" : 25.0,
        "sulphur_dioxide"  : 5.0,
    }
    for col, val in baseline.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)

    # Derived features
    df["heat_index"] = df.apply(
        lambda r: compute_heat_index(r["temperature"], r["humidity"], r["wind"]),
        axis=1,
    )
    df["pollution_level"] = df.apply(
        lambda r: compute_pollution_level(r["pm25"], r["pm10"], r["aqi"]),
        axis=1,
    )
    df["respiratory_stress"] = df.apply(
        lambda r: compute_respiratory_stress(
            r["pm25"], r["ozone"], r["nitrogen_dioxide"], r["sulphur_dioxide"]
        ),
        axis=1,
    )
    df["uv_risk"] = compute_uv_risk()   # 0 until UV forecast source added

    df["processed_at"] = datetime.now(timezone.utc).isoformat()

    # Column order matches training data
    cols = [
        "date", "horizon",
        "temperature", "humidity", "wind", "pressure", "cloud_cover",
        "pm25", "pm10", "aqi", "ozone", "nitrogen_dioxide", "sulphur_dioxide",
        "heat_index", "pollution_level", "respiratory_stress", "uv_risk",
        "processed_at",
    ]
    df = df[[c for c in cols if c in df.columns]]

    log.info("Engineered features for %d forecast days", len(df))
    for _, row in df.iterrows():
        log.info(
            "  Day +%d (%s) → heat_index=%.1f  pollution_level=%.1f  resp_stress=%.1f",
            row["horizon"], row["date"],
            row["heat_index"], row["pollution_level"], row["respiratory_stress"],
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