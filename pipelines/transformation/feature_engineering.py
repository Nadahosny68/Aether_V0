import pandas as pd
import json
import os
import sys
from datetime import datetime

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STAGING_DIR = os.path.join(ROOT, "data", "staging")
PROCESSED   = os.path.join(ROOT, "data", "processed")
RAW_DIR     = os.path.join(ROOT, "data", "raw")

os.makedirs(PROCESSED, exist_ok=True)


# ── Health category ────────────────────────────────────────────────────────
def classify_health(row):
    aqi   = row.get("aqi")              or 0
    pm25  = row.get("pm25")             or 0
    ozone = row.get("ozone")            or 0
    no2   = row.get("nitrogen_dioxide") or 0
    hi    = row.get("heat_index")       or 0

    if aqi > 110 or pm25 > 50:
        return "Avoid Outdoor Activity Day"

    elif aqi > 85 or pm25 > 30 or hi > 48:
        return "Mask Recommended Day"

    elif aqi > 70 or pm25 > 20 or ozone > 80:
        return "High Respiratory Risk Day"

    elif aqi > 55 or pm25 > 14 or no2 > 30:
        return "Moderate Risk Day"

    else:
        return "Safe Air Day"


# ── Load and merge historical CSVs ─────────────────────────────────────────
def load_historical():
    print("  Loading historical staging files...")

    weather   = pd.read_csv(os.path.join(STAGING_DIR, "weather_clean.csv"))
    pollution = pd.read_csv(os.path.join(STAGING_DIR, "pollution_clean.csv"))

    print(f"  Weather rows before merge:    {len(weather)}")
    print(f"  Pollution rows before merge:  {len(pollution)}")

    weather["date"]   = pd.to_datetime(weather["date"],   errors="coerce").dt.date
    pollution["date"] = pd.to_datetime(pollution["date"], errors="coerce").dt.date

    df = pd.merge(weather, pollution, on="date", how="inner")

    print(f"  Merged rows (date overlap):   {len(df)}")
    return df


# ── Compute derived features ───────────────────────────────────────────────
def add_features(df):
    temp = df["temperature"] if "temperature" in df.columns else 0
    hum  = df["humidity"]    if "humidity"    in df.columns else 0
    wind = df["wind"]        if "wind"        in df.columns else 0
    pm25 = df["pm25"].fillna(0) if "pm25" in df.columns else 0
    pm10 = df["pm10"].fillna(0) if "pm10" in df.columns else 0
    aqi  = df["aqi"].fillna(0)  if "aqi"  in df.columns else 0
    no2  = df["nitrogen_dioxide"].fillna(0) if "nitrogen_dioxide" in df.columns else 0
    so2  = df["sulphur_dioxide"].fillna(0)  if "sulphur_dioxide"  in df.columns else 0
    oz   = df["ozone"].fillna(0)            if "ozone"            in df.columns else 0

    df["heat_index"]        = temp + (0.33 * hum) - (0.70 * wind)
    df["pollution_level"]   = (pm25 * 0.5) + (pm10 * 0.3) + (aqi * 0.2)
    df["respiratory_stress"]= (pm25 * 0.4) + (oz * 0.3) + (no2 * 0.2) + (so2 * 0.1)

    if "uv_index" in df.columns:
        df["uv_risk"] = (df["uv_index"].fillna(0) / 11 * 100).clip(0, 100)
    else:
        df["uv_risk"] = 0

    df["health_category"] = df.apply(
        lambda row: classify_health(row.to_dict()), axis=1
    )

    print(f"\n  Features created:")
    print(f"    heat_index, pollution_level, respiratory_stress, uv_risk, health_category")
    print(f"\n  Health category distribution:")
    print(df["health_category"].value_counts().to_string())

    return df


# ── Main ───────────────────────────────────────────────────────────────────
def run():
    print("Starting feature engineering (historical mode)...")

    df = load_historical()
    df = add_features(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    out_path = os.path.join(PROCESSED, "environmental_features.csv")
    df.to_csv(out_path, index=False)

    print(f"\n  Final rows:    {len(df)}")
    print(f"  Final columns: {list(df.columns)}")
    print(f"  Saved to:      {out_path}")
    print("\nFeature engineering completed.")


if __name__ == "__main__":
    run()

# No mode switching, no API logic, no command line arguments needed. It always reads from `data/staging/weather_clean.csv` and `data/staging/pollution_clean.csv`, merges on date, computes all features, and saves one combined file to `data/processed/environmental_features.csv`.

# Run it from the terminal:
# python pipelines/transformation/feature_engineering.py