"""
pipelines/transformation/data_cleaning.py
──────────────────────────────────────────
Cleans historical weather and pollution CSVs.

Root cause of 0 pollution rows — fixed here:
  The format="%y/%m/%d" and dayfirst=True attempts both converted
  every "2022-08-01" date to NaT because they forced the wrong
  interpretation. The date is plain ISO — no format override needed.

Weather date:    "2000-01-01 00:00:00+00:00" → strip timezone → date
Pollution date:  "2022-08-01" → standard ISO parse → date
"""

import pandas as pd
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

WEATHER_RAW   = os.path.join(ROOT, "data", "raw", "cairo_weather_historical.csv")
POLLUTION_RAW = os.path.join(ROOT, "data", "raw", "cairo_airquality_historical.csv")
STAGING_DIR   = os.path.join(ROOT, "data", "staging")

os.makedirs(STAGING_DIR, exist_ok=True)


def clean_weather():
    print("\n--- Weather Dataset ---")
    df = pd.read_csv(WEATHER_RAW)
    print(f"  Rows loaded: {len(df)}")

    df = df.drop_duplicates()

    df = df.rename(columns={
        "temperature_2m_mean"        : "temperature",
        "relative_humidity_2m_mean"  : "humidity",
        "wind_speed_10m_mean"        : "wind",
        "pressure_msl_mean"          : "pressure",
        "cloud_cover_mean"           : "cloud_cover",
        "sunshine_duration"          : "sunshine_duration",
        "temperature_2m_max"         : "temp_max",
        "temperature_2m_min"         : "temp_min",
        "apparent_temperature_max"   : "apparent_temp_max",
        "apparent_temperature_min"   : "apparent_temp_min",
        "apparent_temperature_mean"  : "apparent_temp_mean",
        "relative_humidity_2m_max"   : "humidity_max",
        "relative_humidity_2m_min"   : "humidity_min",
        "wind_speed_10m_max"         : "wind_max",
        "wind_gusts_10m_max"         : "wind_gust_max",
        "precipitation_sum"          : "precipitation",
        "rain_sum"                   : "rain_sum",
        "dew_point_2m_mean"          : "dew_point",
        "shortwave_radiation_sum"    : "shortwave_radiation",
        "vapour_pressure_deficit_max": "vapour_pressure_deficit",
    })

    keep = [
        "date",
        "temperature", "humidity", "wind", "pressure", "cloud_cover",
        "sunshine_duration",
        "temp_max", "temp_min",
        "apparent_temp_max", "apparent_temp_min", "apparent_temp_mean",
        "humidity_max", "humidity_min",
        "wind_max", "wind_gust_max",
        "precipitation", "rain_sum",
        "dew_point", "shortwave_radiation", "vapour_pressure_deficit",
    ]
    df = df[[c for c in keep if c in df.columns]]

    # Weather date: "2000-01-01 00:00:00+00:00" — has timezone, strip it
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["date"] = df["date"].dt.tz_localize(None).dt.date

    critical = ["date", "temperature", "humidity", "wind"]
    before = len(df)
    df = df.dropna(subset=critical)
    print(f"  Rows dropped (missing critical): {before - len(df)}")

    for col in [c for c in df.columns if c not in critical]:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    print(f"  Weather cleaned: {len(df)} rows")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    return df


def clean_pollution():
    print("\n--- Pollution Dataset ---")
    df = pd.read_csv(POLLUTION_RAW)
    print(f"  Rows loaded: {len(df)}")

    df = df.drop_duplicates()

    df = df.rename(columns={
        "pm2_5"  : "pm25",
        "us_aqi" : "aqi",
    })

    keep = [
        "date", "pm25", "pm10", "aqi", "european_aqi",
        "ozone", "nitrogen_dioxide", "sulphur_dioxide",
        "dust", "uv_index", "carbon_monoxide", "aerosol_optical_depth",
    ]
    df = df[[c for c in keep if c in df.columns]]

    # ── THE ACTUAL FIX ────────────────────────────────────────────────────────
    # Pollution date is plain ISO "2022-08-01" — no format override needed.
    # format="%y/%m/%d" → NaT (wrong year spec)
    # dayfirst=True     → NaT (still wrong)
    # Correct: just let pandas parse it normally
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date"] = df["date"].dt.date
    # ─────────────────────────────────────────────────────────────────────────

    # Only drop rows where the date itself failed to parse
    before = len(df)
    df = df.dropna(subset=["date"])
    print(f"  Rows dropped (unparseable date): {before - len(df)}")

    # Fill numeric nulls with median — do NOT drop rows for missing AQI
    # Your first 3 rows are all NaN but dates are valid — keep them, fill values
    for col in [c for c in df.columns if c != "date"]:
        if df[col].isnull().any():
            n = df[col].isnull().sum()
            df[col] = df[col].fillna(df[col].median())
            print(f"  Filled {n} nulls in '{col}' with median")

    print(f"  Pollution cleaned: {len(df)} rows")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    return df


def validate_and_find_gaps(weather: pd.DataFrame, pollution: pd.DataFrame):
    print("\n--- Overlap & Gap Analysis ---")

    w_dates = set(weather["date"])
    p_dates = set(pollution["date"])
    common  = w_dates & p_dates

    print(f"  Weather dates:   {len(w_dates)}  ({min(w_dates)} → {max(w_dates)})")
    print(f"  Pollution dates: {len(p_dates)}  ({min(p_dates)} → {max(p_dates)})")
    print(f"  Common dates:    {len(common)}")

    overlap_start = max(min(w_dates), min(p_dates))
    overlap_end   = min(max(w_dates), max(p_dates))
    full_range    = set(pd.date_range(str(overlap_start), str(overlap_end)).date)
    missing       = sorted(full_range - p_dates)

    print(f"  Overlap period:  {overlap_start} → {overlap_end}")
    print(f"  Expected days:   {len(full_range)}")
    print(f"  Missing days:    {len(missing)}")

    if missing:
        print(f"  First 5 missing: {missing[:5]}")
        out = os.path.join(STAGING_DIR, "missing_pollution_dates.csv")
        pd.DataFrame({"date": missing}).to_csv(out, index=False)
        print(f"  Saved gap list → {out}")

    return missing


def run():
    print("Starting cleaning pipeline...")

    weather   = clean_weather()
    pollution = clean_pollution()

    weather.to_csv(os.path.join(STAGING_DIR, "weather_clean.csv"),    index=False)
    pollution.to_csv(os.path.join(STAGING_DIR, "pollution_clean.csv"), index=False)

    missing = validate_and_find_gaps(weather, pollution)

    print("\n--- Final Summary ---")
    print(f"  Weather rows:   {len(weather)}")
    print(f"  Pollution rows: {len(pollution)}")
    print(f"  Gap days:       {len(missing)}")
    if missing:
        print(f"  Next step: run fill_pollution_gaps.py to fetch {len(missing)} missing days")
    print("Cleaning completed.")


if __name__ == "__main__":
    run()