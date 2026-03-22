import pandas as pd
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

WEATHER_RAW   = os.path.join(ROOT, "data", "raw", "cairo_weather_historical.csv")
POLLUTION_RAW = os.path.join(ROOT, "data", "raw", "cairo_airquality_historical.csv")
STAGING_DIR   = os.path.join(ROOT, "data", "staging")

os.makedirs(STAGING_DIR, exist_ok=True)


# ── WEATHER CLEANING ───────────────────────────────────────────────────────
def clean_weather():
    print("\n--- Weather Dataset ---")
    df = pd.read_csv(WEATHER_RAW)

    print(f"  Rows loaded:      {len(df)}")
    print(f"  Columns:          {list(df.columns)}")
    print(f"  Nulls per column:\n{df.isnull().sum()[df.isnull().sum() > 0]}")

    # Step 1: Remove exact duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Duplicates removed: {before - len(df)}")

    # Step 2: Rename FIRST so all further work uses clean names
    df = df.rename(columns={
        "date":                      "date",
        "temperature_2m_mean":       "temperature",
        "relative_humidity_2m_mean": "humidity",
        "wind_speed_10m_mean":       "wind",
        "pressure_msl_mean":         "pressure",
        "cloud_cover_mean":          "cloud_cover",
        "sunshine_duration":         "sunshine_duration",
    })

    # Step 3: Keep only the columns Aether needs
    keep = ["date", "temperature", "humidity", "wind",
            "pressure", "cloud_cover", "sunshine_duration"]
    existing = [c for c in keep if c in df.columns]
    df = df[existing]

    # Step 4: Drop rows only where the critical columns are null
    # (temperature, humidity, wind are essential — date is always required)
    critical = ["date", "temperature", "humidity", "wind"]
    before = len(df)
    df = df.dropna(subset=critical)
    print(f"  Rows dropped (missing critical): {before - len(df)}")

    # Step 5: Fill non-critical nulls with column median
    for col in ["pressure", "cloud_cover", "sunshine_duration"]:
        if col in df.columns and df[col].isnull().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            print(f"  Filled nulls in '{col}' with median: {round(median_val, 2)}")

    # Step 6: Normalize date
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    print(f"  Final rows: {len(df)}")
    return df


# ── POLLUTION CLEANING ─────────────────────────────────────────────────────
def clean_pollution():
    print("\n--- Pollution Dataset ---")
    df = pd.read_csv(POLLUTION_RAW)

    print(f"  Rows loaded:      {len(df)}")
    print(f"  Columns:          {list(df.columns)}")
    print(f"  Nulls per column:\n{df.isnull().sum()[df.isnull().sum() > 0]}")

    # Step 1: Remove duplicates
    before = len(df)
    df = df.drop_duplicates()
    print(f"  Duplicates removed: {before - len(df)}")

    # Step 2: Rename FIRST
    df = df.rename(columns={
        "date":             "date",
        "pm2_5":            "pm25",
        "pm10":             "pm10",
        "us_aqi":           "aqi",
        "european_aqi":     "european_aqi",
        "ozone":            "ozone",
        "nitrogen_dioxide": "nitrogen_dioxide",
        "sulphur_dioxide":  "sulphur_dioxide",
        "dust":             "dust",
        "uv_index":         "uv_index",
    })

    # Step 3: Keep only what Aether needs
    keep = ["date", "pm25", "pm10", "aqi", "european_aqi",
            "ozone", "nitrogen_dioxide", "sulphur_dioxide",
            "dust", "uv_index"]
    existing = [c for c in keep if c in df.columns]
    df = df[existing]

    # Step 4: Drop rows only where AQI or PM2.5 are missing
    # (these are the core pollution metrics — without them the row is useless)
    critical = ["date", "aqi"]
    before = len(df)
    df = df.dropna(subset=critical)
    print(f"  Rows dropped (missing critical): {before - len(df)}")

    # Step 5: Fill remaining nulls with column median
    fill_cols = ["pm25", "pm10", "ozone", "nitrogen_dioxide",
                "sulphur_dioxide", "dust", "uv_index", "european_aqi"]
    for col in fill_cols:
        if col in df.columns and df[col].isnull().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            print(f"  Filled nulls in '{col}' with median: {round(median_val, 2)}")

    # Step 6: Normalize date
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    print(f"  Final rows: {len(df)}")
    return df


# ── SAVE ───────────────────────────────────────────────────────────────────
def run():
    print("Starting cleaning pipeline...")
    print("NOTE: API data is handled separately in feature_engineering.py")
    print("      This script only cleans historical CSV files.")

    weather   = clean_weather()
    pollution = clean_pollution()

    weather.to_csv(os.path.join(STAGING_DIR, "weather_clean.csv"),   index=False)
    pollution.to_csv(os.path.join(STAGING_DIR, "pollution_clean.csv"), index=False)

    print("\n--- Summary ---")
    print(f"  Weather rows saved:   {len(weather)}")
    print(f"  Pollution rows saved: {len(pollution)}")
    print(f"  Saved to: {STAGING_DIR}")
    print("Cleaning completed.")


if __name__ == "__main__":
    run()
