"""
pipelines/loading/append_daily_api_row.py
──────────────────────────────────────────
Reads today's fetched API JSON files, computes features,
and appends ONE new row to EnvironmentalFeatures + RiskPredictions.
Runs AFTER load_to_sql.py in the pipeline.
"""

import os, sys, json, pickle
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


def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.environ.get('SQL_SERVER','DESKTOP-Q5KEU1E')};"
        f"DATABASE={os.environ.get('SQL_DATABASE','AetherDW_V0')};"
        "Trusted_Connection=yes;",
        autocommit=False
    )


def load_today_api() -> dict:
    """Load today's weather and pollution from the most recent JSON files."""
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    raw_dir   = os.path.join(ROOT, "data", "raw")

    weather_file   = os.path.join(raw_dir, f"weather_api_{today_str}.json")
    pollution_file = os.path.join(raw_dir, f"pollution_api_{today_str}.json")

    if not os.path.exists(weather_file):
        raise FileNotFoundError(f"No weather API file for today: {weather_file}")
    if not os.path.exists(pollution_file):
        raise FileNotFoundError(f"No pollution API file for today: {pollution_file}")

    with open(weather_file) as f:
        w = json.load(f)
    with open(pollution_file) as f:
        p = json.load(f)

    log.info("Loaded weather: temp=%.1f  humidity=%.0f  wind=%.1f",
            w.get("temperature", 0), w.get("humidity", 0), w.get("wind", 0))
    log.info("Loaded pollution: aqi=%s  pm25=%s",
            p.get("aqi"), p.get("pm25"))
    return w, p


def compute_features(w: dict, p: dict) -> dict:
    temp = w.get("temperature") or 0
    hum  = w.get("humidity")    or 0
    wind = w.get("wind")        or 0
    pm25 = p.get("pm25")        or 0
    pm10 = p.get("pm10")        or 0
    aqi  = p.get("aqi")         or 0
    no2  = p.get("nitrogen_dioxide") or 0
    so2  = p.get("sulphur_dioxide")  or 0
    oz   = p.get("ozone")       or 0

    return {
        "date"               : date.today(),
        "temperature"        : temp,
        "humidity"           : hum,
        "wind"               : wind,
        "pressure"           : w.get("pressure"),
        "cloud_cover"        : w.get("cloud_cover"),
        "pm25"               : pm25,
        "pm10"               : pm10,
        "aqi"                : aqi,
        "ozone"              : oz,
        "nitrogen_dioxide"   : no2,
        "sulphur_dioxide"    : so2,
        "heat_index"         : temp + (0.33 * hum) - (0.70 * wind),
        "pollution_level"    : (pm25 * 0.5) + (pm10 * 0.3) + (aqi * 0.2),
        "respiratory_stress" : (pm25 * 0.4) + (oz * 0.3) + (no2 * 0.2) + (so2 * 0.1),
        "uv_risk"            : 0,
        "temp_range"         : 0,
        "heat_stress_peak"   : temp + (0.33 * hum) - (0.70 * wind),
        "dust_risk_index"    : 0,
        "rain_wash_effect"   : 0,
        "source"             : "api_daily",
    }


def already_exists(conn, today: date) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.EnvironmentalFeatures WHERE date = ?",
        str(today)
    )
    return cursor.fetchone()[0] > 0


def classify_health(row: dict) -> str:
    aqi  = row.get("aqi")  or 0
    pm25 = row.get("pm25") or 0
    if aqi > 150 or pm25 > 65:  return "Avoid Outdoor Activity Day"
    elif aqi > 120 or pm25 > 50: return "Mask Recommended Day"
    elif aqi > 90  or pm25 > 35: return "High Respiratory Risk Day"
    elif aqi > 50  or pm25 > 12: return "Moderate Risk Day"
    else:                         return "Safe Air Day"


def append_to_ef(conn, row: dict) -> None:
    row["health_category"] = classify_health(row)
    log.info("Today's health category: %s (AQI=%s, PM2.5=%s)",
            row["health_category"], row["aqi"], row["pm25"])

    cols = [k for k in row.keys()]
    placeholders = ",".join(["?"] * len(cols))
    col_list = ",".join(cols)
    vals = [row[c] for c in cols]
    vals = [None if (isinstance(v, float) and v != v) else v for v in vals]

    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO dbo.EnvironmentalFeatures ({col_list}) VALUES ({placeholders})",
        vals
    )
    conn.commit()
    log.info("Appended today's row to EnvironmentalFeatures: %s", row["date"])


def append_to_rp(conn, row: dict) -> None:
    """Append prediction to RiskPredictions if not already there."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM dbo.RiskPredictions WHERE date = ?",
        str(row["date"])
    )
    if cursor.fetchone()[0] > 0:
        log.info("RiskPredictions already has entry for %s — skipping", row["date"])
        return

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(FEATURES_PATH, "rb") as f:
        feature_cols = pickle.load(f)

    df = pd.DataFrame([row])
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    X = df[feature_cols].fillna(0)

    prediction  = model.predict(X)[0]
    probability = model.predict_proba(X).max()

    cursor.execute("""
        INSERT INTO RiskPredictions
            (date, temperature, humidity, wind, heat_index,
            pm25, pm10, aqi, pollution_level, respiratory_stress, uv_risk,
            temp_range, heat_stress_peak, dust_risk_index, rain_wash_effect,
            health_category, model_version, predicted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """,
        str(row["date"]),
        row.get("temperature"), row.get("humidity"), row.get("wind"),
        row.get("heat_index"), row.get("pm25"), row.get("pm10"),
        row.get("aqi"), row.get("pollution_level"), row.get("respiratory_stress"),
        row.get("uv_risk"), row.get("temp_range"), row.get("heat_stress_peak"),
        row.get("dust_risk_index"), row.get("rain_wash_effect"),
        prediction, "v2.1", datetime.now()
    )
    conn.commit()
    log.info("Appended to RiskPredictions: %s → %s (%.0f%%)",
             row["date"], prediction, probability * 100)


def run():
    log.info("Appending today's API data to EnvironmentalFeatures …")
    w, p = load_today_api()
    row  = compute_features(w, p)
    conn = get_conn()

    try:
        if already_exists(conn, row["date"]):
            log.info("Today's date %s already in EnvironmentalFeatures — skipping", row["date"])
        else:
            append_to_ef(conn, row)

        append_to_rp(conn, row)
    finally:
        conn.close()


if __name__ == "__main__":
    run()