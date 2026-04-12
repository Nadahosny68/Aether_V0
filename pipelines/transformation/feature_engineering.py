"""
pipelines/transformation/feature_engineering.py
─────────────────────────────────────────────────
Merges weather + pollution staging files, computes all health features,
and classifies each day into a health category.

v2.1 changes:
- Fixed AOD thresholds to match actual data range (max=0.783, not 2.5+)
- Restored Moderate threshold to AQI>55 (AQI>60 was pushing too many
days into Safe Air which is unrealistic for Cairo mean AQI of 73)
- Storm detection now uses calibrated thresholds based on real data stats:
    dust mean=36.9, std=54.8, max=574 → storm threshold = 200+
    AOD  mean=0.205, std=0.099, max=0.783 → storm threshold = 0.55+
    wind_max → storm threshold = 45+ km/h
- Added aerosol_optical_depth and carbon_monoxide as model features

Storm day logic (Cairo-specific):
Cairo experiences two types of extreme dust events:
1. Khamaseen (spring): high AOD + high dust + hot dry wind
2. General sandstorm: extreme dust loading even without classic conditions
Both captured by the updated thresholds below.
"""

import pandas as pd
import os

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STAGING_DIR = os.path.join(ROOT, "data", "staging")
PROCESSED   = os.path.join(ROOT, "data", "processed")

os.makedirs(PROCESSED, exist_ok=True)


# ── Health classification ──────────────────────────────────────────────────────
def classify_health(row):
    aqi          = row.get("aqi")          or 0
    pm25         = row.get("pm25")         or 0
    ozone        = row.get("ozone")        or 0
    no2          = row.get("nitrogen_dioxide") or 0
    hi           = row.get("heat_index")   or 0
    heat_peak    = row.get("heat_stress_peak") or 0
    dust         = row.get("dust_risk_index")  or 0
    rain         = row.get("rain_wash_effect") or 0
    wind_max     = row.get("wind_max")     or 0
    humidity_min = row.get("humidity_min") or 50
    aod          = row.get("aerosol_optical_depth") or 0
    raw_dust     = row.get("dust")         or 0

    rain_factor    = max(0.5, 1 - rain * 0.05)
    effective_aqi  = aqi  * rain_factor
    effective_pm25 = pm25 * rain_factor

    # Storm detection (unchanged - calibrated correctly)
    storm = (
        (wind_max > 40 and humidity_min < 20 and dust > 25)
        or (raw_dust > 200)
        or (aod > 0.55 and wind_max > 35)
    )
    if storm:
        return "Avoid Outdoor Activity Day"

    # Recalibrated to match IQAir/AQI.in scale for Cairo
    if effective_aqi > 150 or effective_pm25 > 65:
        return "Avoid Outdoor Activity Day"

    elif effective_aqi > 120 or effective_pm25 > 50 or heat_peak > 54:
        return "Mask Recommended Day"

    elif effective_aqi > 90 or effective_pm25 > 35 or ozone > 100 or dust > 30 or aod > 0.40:
        return "High Respiratory Risk Day"

    elif effective_aqi > 50 or effective_pm25 > 12 or no2 > 40:
        return "Moderate Risk Day"

    else:
        return "Safe Air Day"


# ── Load historical staging files ─────────────────────────────────────────────
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


# ── Compute all features ───────────────────────────────────────────────────────
def add_features(df: pd.DataFrame) -> pd.DataFrame:

    def col(name, default=0):
        return df[name].fillna(default) if name in df.columns else \
               pd.Series([default] * len(df), index=df.index)

    # ── Original mean-based features ──────────────────────────────────────────
    df["heat_index"]         = col("temperature") + (0.33 * col("humidity")) \
                               - (0.70 * col("wind"))
    df["pollution_level"]    = (col("pm25") * 0.5) + (col("pm10") * 0.3) \
                               + (col("aqi") * 0.2)
    df["respiratory_stress"] = (col("pm25") * 0.4) + (col("ozone") * 0.3) \
                               + (col("nitrogen_dioxide") * 0.2) \
                               + (col("sulphur_dioxide") * 0.1)

    if "uv_index" in df.columns:
        df["uv_risk"] = (df["uv_index"].fillna(0) / 11 * 100).clip(0, 100)
    else:
        df["uv_risk"] = 0

    # ── New v2 max/min-derived features ───────────────────────────────────────
    if "temp_max" in df.columns and "temp_min" in df.columns:
        df["temp_range"] = col("temp_max") - col("temp_min")
    else:
        df["temp_range"] = 0

    if "apparent_temp_max" in df.columns:
        df["heat_stress_peak"] = col("apparent_temp_max")
    else:
        df["heat_stress_peak"] = col("temp_max")

    if "wind_max" in df.columns and "humidity_min" in df.columns:
        df["dust_risk_index"] = col("wind_max") * (1 - col("humidity_min") / 100)
    else:
        df["dust_risk_index"] = 0

    df["rain_wash_effect"] = col("precipitation").clip(0, 20) \
                            if "precipitation" in df.columns else 0

    # ── Storm-specific: keep raw columns accessible to classify_health ─────────
    # aerosol_optical_depth and dust are already in df from the merge
    # (they come from pollution_clean.csv) — no need to recompute

    # ── Health category ────────────────────────────────────────────────────────
    df["health_category"] = df.apply(
        lambda row: classify_health(row.to_dict()), axis=1
    )

    # Print calibrated distribution
    categories = [
        "Safe Air Day",
        "Moderate Risk Day",
        "High Respiratory Risk Day",
        "Mask Recommended Day",
        "Avoid Outdoor Activity Day",
    ]
    dist = df["health_category"].value_counts()

    print("\n  Health category distribution:")
    total = len(df)
    for c in categories:
        n   = dist.get(c, 0)
        pct = round(n / total * 100, 1)
        print(f"    {c:<35} {n:>4}  ({pct}%)")

    # Sanity check — warn if Safe Air Day seems unrealistically high
    safe_pct = dist.get("Safe Air Day", 0) / total * 100
    if safe_pct > 15:
        print(f"\n  ⚠ WARNING: Safe Air Day is {safe_pct:.1f}% of days.")
        print(f"    Cairo mean AQI=73. If Safe Air >15%, check thresholds.")

    return df


# ── Main ───────────────────────────────────────────────────────────────────────
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