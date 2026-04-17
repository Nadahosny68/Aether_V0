"""
pipelines/loading/append_daily_api_row.py
──────────────────────────────────────────
Reads today's fetched API JSON files, computes ALL features,
and appends ONE new row to EnvironmentalFeatures.
Then runs ML inference and writes to RiskPredictions.

This fills today's data gap — EnvironmentalFeatures only has
historical data up to 2025-10-01 from the CSV.

Run order in pipeline:
fetch_weather_api → fetch_pollution_api → feature_engineering
→ load_to_sql → append_daily_api_row → run_predictions
"""

import os
import sys
import json
import pickle
import glob
import pandas as pd
import pyodbc
from datetime import datetime, date, timezone
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from utils.logger import get_logger
log = get_logger("append_daily_api_row")

MODEL_PATH    = os.path.join(ROOT, "ML", "models", "environmental_risk_model.pkl")
FEATURES_PATH = os.path.join(ROOT, "ML", "models", "feature_columns.pkl")
RAW_DIR       = os.path.join(ROOT, "data", "raw")


def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.environ.get('SQL_SERVER', 'DESKTOP-Q5KEU1E')};"
        f"DATABASE={os.environ.get('SQL_DATABASE', 'AetherDW_V0')};"
        "Trusted_Connection=yes;",
        autocommit=False
    )


def load_today_json(prefix: str) -> dict:
    """Load today's JSON file by prefix, fall back to latest file."""
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    exact     = os.path.join(RAW_DIR, f"{prefix}_{today_str}.json")

    if os.path.exists(exact):
        with open(exact) as f:
            return json.load(f)

    # Fallback: find the most recent file with this prefix
    pattern = os.path.join(RAW_DIR, f"{prefix}_*.json")
    files   = sorted(glob.glob(pattern))
    if files:
        latest = files[-1]
        log.warning("Today's %s file not found — using latest: %s",
                    prefix, os.path.basename(latest))
        with open(latest) as f:
            return json.load(f)

    raise FileNotFoundError(
        f"No {prefix}_*.json files found in {RAW_DIR}.\n"
        f"Run fetch_{prefix}_api.py first."
    )


def compute_features(w: dict, p: dict) -> dict:
    """
    Compute all features that can be derived from the API data.
    Columns not available from live APIs (sunshine_duration, dew_point etc.)
    are filled with None so SQL writes NULL — honest and correct.
    """
    temp     = w.get("temperature") or 0
    hum      = w.get("humidity")    or 0
    wind     = w.get("wind")        or 0
    temp_max = w.get("temp_max")    or temp
    temp_min = w.get("temp_min")    or temp
    hum_min  = w.get("humidity_min") or hum
    wind_max = w.get("wind_max")    or wind
    app_max  = w.get("apparent_temp_max") or (temp + (0.33 * hum) - (0.70 * wind))
    precip   = w.get("precipitation") or 0

    pm25  = p.get("pm25") or 0
    pm10  = p.get("pm10") or 0
    aqi   = p.get("aqi")  or 0
    no2   = p.get("nitrogen_dioxide") or 0
    so2   = p.get("sulphur_dioxide")  or 0
    oz    = p.get("ozone")            or 0

    heat_index        = temp + (0.33 * hum) - (0.70 * wind)
    pollution_level   = (pm25 * 0.5) + (pm10 * 0.3) + (aqi * 0.2)
    respiratory_stress= (pm25 * 0.4) + (oz * 0.3) + (no2 * 0.2) + (so2 * 0.1)
    temp_range        = temp_max - temp_min
    heat_stress_peak  = app_max
    dust_risk_index   = wind_max * (1 - hum_min / 100) if hum_min < 100 else 0
    rain_wash_effect  = min(precip, 20)

    return {
        "date"               : str(date.today()),
        "temperature"        : round(temp, 4),
        "humidity"           : round(hum, 4),
        "wind"               : round(wind, 4),
        "pressure"           : w.get("pressure"),
        "cloud_cover"        : w.get("cloud_cover"),
        "temp_max"           : round(temp_max, 4) if temp_max else None,
        "temp_min"           : round(temp_min, 4) if temp_min else None,
        "temp_range"         : round(temp_range, 4),
        "apparent_temp_max"  : round(app_max, 4),
        "apparent_temp_min"  : w.get("apparent_temp_min"),
        "apparent_temp_mean" : w.get("apparent_temp_mean"),
        "humidity_max"       : w.get("humidity_max"),
        "humidity_min"       : round(hum_min, 4) if hum_min else None,
        "wind_max"           : round(wind_max, 4) if wind_max else None,
        "wind_gust_max"      : w.get("wind_gust_max"),
        "precipitation"      : round(precip, 4),
        "pm25"               : pm25,
        "pm10"               : pm10 if pm10 else None,
        "aqi"                : aqi,
        "ozone"              : oz if oz else None,
        "nitrogen_dioxide"   : no2 if no2 else None,
        "sulphur_dioxide"    : so2 if so2 else None,
        "heat_index"         : round(heat_index, 4),
        "pollution_level"    : round(pollution_level, 4),
        "respiratory_stress" : round(respiratory_stress, 4),
        "uv_risk"            : 0,
        "heat_stress_peak"   : round(heat_stress_peak, 4),
        "dust_risk_index"    : round(dust_risk_index, 4),
        "rain_wash_effect"   : round(rain_wash_effect, 4),
        "source"             : "api_daily",
    }


def classify_health(row: dict) -> str:
    """
    Same thresholds as feature_engineering.py — must stay in sync.
    """
    aqi   = row.get("aqi")  or 0
    pm25  = row.get("pm25") or 0
    rain  = row.get("rain_wash_effect") or 0

    rain_factor    = max(0.5, 1 - rain * 0.05)
    effective_aqi  = aqi  * rain_factor
    effective_pm25 = pm25 * rain_factor

    if effective_aqi > 150 or effective_pm25 > 65:
        return "Avoid Outdoor Activity Day"
    elif effective_aqi > 120 or effective_pm25 > 50:
        return "Mask Recommended Day"
    elif effective_aqi > 90  or effective_pm25 > 35:
        return "High Respiratory Risk Day"
    elif effective_aqi > 50  or effective_pm25 > 12:
        return "Moderate Risk Day"
    else:
        return "Safe Air Day"


def already_in_ef(conn, today: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.EnvironmentalFeatures "
        "WHERE date = ? AND source = 'api_daily'",
        today
    )
    return cursor.fetchone()[0] > 0


def insert_ef(conn, row: dict) -> None:
    row["health_category"] = classify_health(row)
    log.info("Rule-based category: %s  (AQI=%.0f, PM2.5=%.1f)",
            row["health_category"], row.get("aqi", 0), row.get("pm25", 0))

    cols = list(row.keys())
    sql  = (
        f"INSERT INTO dbo.EnvironmentalFeatures "
        f"({', '.join(cols)}) "
        f"VALUES ({', '.join(['?'] * len(cols))})"
    )
    vals = []
    for c in cols:
        v = row[c]
        if v is None:
            vals.append(None)
        elif isinstance(v, float) and v != v:  # NaN check
            vals.append(None)
        elif hasattr(v, "item"):               # numpy scalar
            vals.append(v.item())
        else:
            vals.append(v)

    cursor = conn.cursor()
    cursor.execute(sql, vals)
    conn.commit()
    log.info("Inserted today's row into EnvironmentalFeatures: %s", row["date"])


def run_ml_prediction(row: dict) -> tuple:
    """Run ML model on today's features. Returns (category, confidence)."""
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(FEATURES_PATH, "rb") as f:
        feature_cols = pickle.load(f)

    df = pd.DataFrame([row])
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0.0
    df[feature_cols] = df[feature_cols].fillna(0.0)

    category   = model.predict(df[feature_cols])[0]
    confidence = model.predict_proba(df[feature_cols]).max()
    return category, confidence


def already_in_rp(conn, today: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.RiskPredictions WHERE date = ?", today
    )
    return cursor.fetchone()[0] > 0


def insert_rp(conn, row: dict, category: str, confidence: float) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO RiskPredictions
            (date, temperature, humidity, wind, heat_index,
            pm25, pm10, aqi, pollution_level, respiratory_stress, uv_risk,
            temp_range, heat_stress_peak, dust_risk_index, rain_wash_effect,
            health_category, model_version, predicted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """,
        row["date"],
        row.get("temperature"), row.get("humidity"), row.get("wind"),
        row.get("heat_index"),
        row.get("pm25"), row.get("pm10"), row.get("aqi"),
        row.get("pollution_level"), row.get("respiratory_stress"),
        row.get("uv_risk"),
        row.get("temp_range"), row.get("heat_stress_peak"),
        row.get("dust_risk_index"), row.get("rain_wash_effect"),
        category, "v2.1", datetime.now()
    )
    conn.commit()
    log.info("Inserted into RiskPredictions: %s → %s (%.0f%%)",
             row["date"], category, confidence * 100)


from datetime import timezone, timedelta

def run():
    log.info("=== append_daily_api_row starting ===")

    # ✅ Cairo timezone
    cairo_tz  = timezone(timedelta(hours=2))
    today_str = datetime.now(cairo_tz).strftime("%Y-%m-%d")

    w = load_today_json("weather_api")
    p = load_today_json("pollution_api")

    log.info("Weather data keys: %s", list(w.keys()))
    log.info("Pollution AQI=%s  PM2.5=%s", p.get("aqi"), p.get("pm25"))

    row  = compute_features(w, p)
    conn = get_conn()

    try:
        # ── EnvironmentalFeatures ──────────────────────────────────────────
        if already_in_ef(conn, today_str):
            log.info("EF already has today's api_daily row — skipping insert")
        else:
            insert_ef(conn, row)

        # ── RiskPredictions ────────────────────────────────────────────────
        if already_in_rp(conn, today_str):
            log.info("RiskPredictions already has today — skipping")
        else:
            category, confidence = run_ml_prediction(row)
            log.info("ML prediction: %s (confidence %.0f%%)",
                     category, confidence * 100)
            insert_rp(conn, row, category, confidence)

    finally:
        conn.close()

    log.info("=== append_daily_api_row complete ===")


if __name__ == "__main__":
    run()