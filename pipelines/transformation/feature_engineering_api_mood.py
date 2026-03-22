import pandas as pd
import json
import os
from datetime import datetime

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STAGING_DIR = os.path.join(ROOT, "data", "staging")
PROCESSED   = os.path.join(ROOT, "data", "processed")
RAW_DIR     = os.path.join(ROOT, "data", "raw")

os.makedirs(PROCESSED, exist_ok=True)


# ── Health category — the core Aether output ──────────────────────────────
def classify_health(row):
    aqi   = row.get("aqi")              or 0
    pm25  = row.get("pm25")             or 0
    ozone = row.get("ozone")            or 0
    no2   = row.get("nitrogen_dioxide") or 0
    hi    = row.get("heat_index")       or 0

    # Thresholds calibrated to Cairo data
    # AQI: mean=70, 25th=60, 75th=76, max=150
    # PM25: mean=21, 25th=16, 75th=24, max=72

    if aqi > 110 or pm25 > 50:
        return "Avoid Outdoor Activity Day"   # top ~3%

    elif aqi > 85 or pm25 > 30 or hi > 48:
        return "Mask Recommended Day"          # top ~15%

    elif aqi > 70 or pm25 > 20 or ozone > 80:
        return "High Respiratory Risk Day"     # around median ~30%

    elif aqi > 55 or pm25 > 14 or no2 > 30:
        return "Moderate Risk Day"             # lower half ~35%

    else:
        return "Safe Air Day"                  # cleanest days ~17%


# ── Compute all derived features ───────────────────────────────────────────
def add_features(df):
    temp = df["temperature"] if "temperature" in df.columns else 0
    hum  = df["humidity"]    if "humidity"    in df.columns else 0
    wind = df["wind"]        if "wind"        in df.columns else 0
    pm25 = df["pm25"].fillna(0) if "pm25" in df.columns else 0
    pm10 = df["pm10"].fillna(0) if "pm10" in df.columns else 0
    aqi  = df["aqi"].fillna(0)  if "aqi"  in df.columns else 0

    # Heat index — perceived temperature combining heat and humidity
    df["heat_index"] = temp + (0.33 * hum) - (0.70 * wind)

    # Pollution level — weighted combination of particulates and AQI
    df["pollution_level"] = (pm25 * 0.5) + (pm10 * 0.3) + (aqi * 0.2)

    # UV risk score — normalized 0 to 100
    if "uv_index" in df.columns:
        df["uv_risk"] = (df["uv_index"].fillna(0) / 11 * 100).clip(0, 100)

    # Respiratory stress index — multi-pollutant combined score
    no2  = df["nitrogen_dioxide"].fillna(0) if "nitrogen_dioxide" in df.columns else 0
    so2  = df["sulphur_dioxide"].fillna(0)  if "sulphur_dioxide"  in df.columns else 0
    oz   = df["ozone"].fillna(0)            if "ozone"            in df.columns else 0
    df["respiratory_stress"] = (pm25 * 0.4) + (oz * 0.3) + (no2 * 0.2) + (so2 * 0.1)

    # Health category — human-readable Aether output
    df["health_category"] = df.apply(
        lambda row: classify_health(row.to_dict()), axis=1
    )

    print(f"  heat_index created")
    print(f"  pollution_level created")
    print(f"  respiratory_stress created")
    print(f"  uv_risk created" if "uv_index" in df.columns else "  uv_risk skipped (no uv_index)")
    print(f"  health_category distribution:\n{df['health_category'].value_counts().to_string()}")

    return df


# ── Mode 1: Load from cleaned historical CSVs and merge on date ────────────
def load_historical():
    print("  Source: historical CSV files")

    weather   = pd.read_csv(os.path.join(STAGING_DIR, "weather_clean.csv"))
    pollution = pd.read_csv(os.path.join(STAGING_DIR, "pollution_clean.csv"))

    # Normalize dates to plain date objects (no time, no timezone)
    weather["date"]   = pd.to_datetime(weather["date"],   errors="coerce").dt.date
    pollution["date"] = pd.to_datetime(pollution["date"], errors="coerce").dt.date

    # ── THIS is where the date-based mapping happens ──
    # Only rows where both datasets have the same date are kept
    df = pd.merge(weather, pollution, on="date", how="inner")

    print(f"  Weather rows:    {len(weather)}")
    print(f"  Pollution rows:  {len(pollution)}")
    print(f"  Merged rows:     {len(df)}  (date overlap only)")

    return df


# ── Mode 2: Load today's live API JSON files ───────────────────────────────
def load_api():
    print("  Source: live API JSON files")

    today          = datetime.utcnow().strftime("%Y%m%d")
    weather_file   = os.path.join(RAW_DIR, f"weather_api_{today}.json")
    pollution_file = os.path.join(RAW_DIR, f"pollution_api_{today}.json")

    if not os.path.exists(weather_file) or not os.path.exists(pollution_file):
        raise FileNotFoundError(
            f"API files for {today} not found. "
            "Run fetch_weather_api.py and fetch_pollution_api.py first."
        )

    with open(weather_file)   as f: w = json.load(f)
    with open(pollution_file) as f: p = json.load(f)

    # API data already shares the same date — no merge needed, just combine
    row = {
        "date":              w.get("date"),
        "temperature":       w.get("temperature"),
        "humidity":          w.get("humidity"),
        "wind":              w.get("wind"),
        "pressure":          w.get("pressure"),
        "pm25":              p.get("pm25"),
        "pm10":              p.get("pm10"),
        "aqi":               p.get("aqi"),
        # Extended fields — not available from these APIs, left as None
        "ozone":             None,
        "nitrogen_dioxide":  None,
        "sulphur_dioxide":   None,
        "dust":              None,
        "uv_index":          None,
        "european_aqi":      None,
        "cloud_cover":       None,
        "sunshine_duration": None,
    }

    print(f"  Single live row for {row['date']}")
    return pd.DataFrame([row])


# ── Main ───────────────────────────────────────────────────────────────────
def run():
    print("Starting feature engineering...")

    today          = datetime.utcnow().strftime("%Y%m%d")
    api_ready      = (
        os.path.exists(os.path.join(RAW_DIR, f"weather_api_{today}.json")) and
        os.path.exists(os.path.join(RAW_DIR, f"pollution_api_{today}.json"))
    )

    df = load_api() if api_ready else load_historical()

    df = add_features(df)

    # Final date cleanup
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    # Save single unified output — this is what SSIS and ML both read
    out_path = os.path.join(PROCESSED, "environmental_features.csv")
    df.to_csv(out_path, index=False)

    print(f"\n  Final rows: {len(df)}")
    print(f"  Final columns: {list(df.columns)}")
    print(f"  Saved to: {out_path}")
    print("Feature engineering completed.")


if __name__ == "__main__":
    run()