"""
ML/inference/predict_forecast.py
─────────────────────────────────
Loads the trained Random Forest model and runs inference on
forecast_features.csv, then upserts results to ForecastPredictions.

Usage:
    python ML/inference/predict_forecast.py
    python ML/inference/predict_forecast.py --dry-run   (print only, no DB write)
"""

import os
import sys
import argparse
import pickle
import pandas as pd
import pyodbc
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv          # ← add this
load_dotenv(os.path.join(ROOT, ".env")) # ← add this

from utils.logger import get_logger

log = get_logger("predict_forecast")

MODEL_PATH    = os.path.join(ROOT, "ML", "models", "environmental_risk_model.pkl")
FEATURES_PATH = os.path.join(ROOT, "data", "processed", "forecast_features.csv")
MODEL_VERSION = "v2.0"

# Must match the feature list used at training time (feature_engineering.py)
FEATURE_COLS = [
    "temperature", "humidity", "wind", "heat_index",
    "pm25", "pm10", "aqi", "pollution_level",
    "respiratory_stress", "uv_risk",
    "pressure", "ozone", "nitrogen_dioxide",
]

# Class label → probability column name
CLASS_PROB_COLS = {
    "Safe Air Day"                : "prob_safe",
    "Moderate Risk Day"           : "prob_moderate",
    "High Respiratory Risk Day"   : "prob_high_resp",
    "Mask Recommended Day"        : "prob_mask",
    "Avoid Outdoor Activity Day"  : "prob_avoid",
}


# ── Load model ─────────────────────────────────────────────────────────────────

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    log.info("Model loaded: %s", MODEL_PATH)
    return model


# ── Load features ──────────────────────────────────────────────────────────────

def load_features() -> pd.DataFrame:
    if not os.path.exists(FEATURES_PATH):
        raise FileNotFoundError(
            f"Forecast features not found: {FEATURES_PATH}\n"
            "Run feature_engineering_forecast.py first."
        )
    df = pd.read_csv(FEATURES_PATH)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    log.info("Loaded forecast features: %d rows", len(df))

    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    return df


# ── Run inference ──────────────────────────────────────────────────────────────

def predict(model, df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURE_COLS]

    predictions  = model.predict(X)
    probabilities = model.predict_proba(X)
    class_labels  = list(model.classes_)

    df = df.copy()
    df["predicted_category"] = predictions
    df["confidence"]         = probabilities.max(axis=1).round(4)

    # Per-class probabilities
    prob_df = pd.DataFrame(probabilities, columns=class_labels, index=df.index)
    for label, col in CLASS_PROB_COLS.items():
        df[col] = prob_df[label].round(4) if label in prob_df.columns else 0.0

    for _, row in df.iterrows():
        log.info(
            "Day +%d (%s) → %-40s (confidence: %.0f%%)",
            row["horizon"], row["date"],
            row["predicted_category"], row["confidence"] * 100,
        )

    return df


# ── Database upsert ────────────────────────────────────────────────────────────

def get_connection() -> pyodbc.Connection:
    server   = os.environ["SQL_SERVER"]
    database = os.environ.get("SQL_DATABASE", "AetherDW_V0")
    driver   = os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


UPSERT_SQL = """
MERGE dbo.ForecastPredictions AS target
USING (VALUES (?, ?, ?, ?)) AS src (forecast_date, forecast_horizon, model_version, generated_at)
ON  target.forecast_date     = src.forecast_date
AND target.forecast_horizon  = src.forecast_horizon
AND target.model_version     = src.model_version
WHEN MATCHED THEN
    UPDATE SET
        generated_at        = ?,
        temperature         = ?, humidity       = ?, wind           = ?,
        pressure            = ?, cloud_cover    = ?,
        pm25                = ?, pm10           = ?, aqi            = ?,
        ozone               = ?, nitrogen_dioxide = ?, sulphur_dioxide = ?,
        heat_index          = ?, pollution_level  = ?,
        respiratory_stress  = ?, uv_risk          = ?,
        predicted_category  = ?, confidence       = ?,
        prob_safe           = ?, prob_moderate    = ?, prob_high_resp  = ?,
        prob_mask           = ?, prob_avoid       = ?
WHEN NOT MATCHED THEN
    INSERT (
        forecast_date, forecast_horizon, generated_at, model_version,
        temperature, humidity, wind, pressure, cloud_cover,
        pm25, pm10, aqi, ozone, nitrogen_dioxide, sulphur_dioxide,
        heat_index, pollution_level, respiratory_stress, uv_risk,
        predicted_category, confidence,
        prob_safe, prob_moderate, prob_high_resp, prob_mask, prob_avoid
    )
    VALUES (
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?,
        ?, ?, ?, ?, ?
    );
"""


def upsert(df: pd.DataFrame) -> None:
    conn   = get_connection()
    cursor = conn.cursor()
    now    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows_affected = 0

    for _, row in df.iterrows():
        vals_match = (
            str(row["date"]), int(row["horizon"]), MODEL_VERSION, now,
        )
        vals_update = (
            now,
            row.get("temperature"), row.get("humidity"), row.get("wind"),
            row.get("pressure"),    row.get("cloud_cover"),
            row.get("pm25"),        row.get("pm10"),     row.get("aqi"),
            row.get("ozone"),       row.get("nitrogen_dioxide"), row.get("sulphur_dioxide"),
            row.get("heat_index"),  row.get("pollution_level"),
            row.get("respiratory_stress"), row.get("uv_risk"),
            row["predicted_category"], row["confidence"],
            row.get("prob_safe"),   row.get("prob_moderate"), row.get("prob_high_resp"),
            row.get("prob_mask"),   row.get("prob_avoid"),
        )
        vals_insert = (
            str(row["date"]), int(row["horizon"]), now, MODEL_VERSION,
            row.get("temperature"), row.get("humidity"), row.get("wind"),
            row.get("pressure"),    row.get("cloud_cover"),
            row.get("pm25"),        row.get("pm10"),     row.get("aqi"),
            row.get("ozone"),       row.get("nitrogen_dioxide"), row.get("sulphur_dioxide"),
            row.get("heat_index"),  row.get("pollution_level"),
            row.get("respiratory_stress"), row.get("uv_risk"),
            row["predicted_category"], row["confidence"],
            row.get("prob_safe"),   row.get("prob_moderate"), row.get("prob_high_resp"),
            row.get("prob_mask"),   row.get("prob_avoid"),
        )
        cursor.execute(UPSERT_SQL, vals_match + vals_update + vals_insert)
        rows_affected += cursor.rowcount

    conn.commit()
    conn.close()
    log.info("Upserted %d forecast rows → ForecastPredictions", rows_affected)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print predictions without writing to database")
    args = parser.parse_args()

    model    = load_model()
    features = load_features()
    results  = predict(model, features)

    if args.dry_run:
        log.info("Dry run — skipping database write")
        print(results[["date", "horizon", "predicted_category", "confidence"]].to_string())
        return

    upsert(results)
    log.info("Forecast pipeline complete")


if __name__ == "__main__":
    main()