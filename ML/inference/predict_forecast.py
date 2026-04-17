"""
ML/inference/predict_forecast.py
─────────────────────────────────
Loads the trained model and runs inference on forecast_features.csv,
then upserts results into ForecastPredictions.

Fixed: UPSERT now includes temp_range, heat_stress_peak,
       dust_risk_index, rain_wash_effect in both UPDATE and INSERT.
"""

import os
import sys
import argparse
import pickle
import pandas as pd
import pyodbc
from datetime import datetime, timezone
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from utils.logger import get_logger
log = get_logger("predict_forecast")

MODEL_PATH    = os.path.join(ROOT, "ML", "models", "environmental_risk_model.pkl")
FEATURES_PATH = os.path.join(ROOT, "ML", "models", "feature_columns.pkl")
DATA_PATH     = os.path.join(ROOT, "data", "processed", "forecast_features.csv")
MODEL_VERSION = "v2.1"

CLASS_PROB_COLS = {
    "Safe Air Day"               : "prob_safe",
    "Moderate Risk Day"          : "prob_moderate",
    "High Respiratory Risk Day"  : "prob_high_resp",
    "Mask Recommended Day"       : "prob_mask",
    "Avoid Outdoor Activity Day" : "prob_avoid",
}


def load_model():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    log.info("Model loaded: %s", MODEL_PATH)
    return model


def load_feature_cols() -> list:
    if os.path.exists(FEATURES_PATH):
        with open(FEATURES_PATH, "rb") as f:
            cols = pickle.load(f)
        log.info("Feature columns loaded: %s", cols)
        return cols
    log.warning("feature_columns.pkl not found — using base feature list")
    return [
        "temperature", "humidity", "wind", "heat_index",
        "pm25", "pm10", "aqi", "pollution_level",
        "respiratory_stress", "uv_risk",
        "pressure", "ozone", "nitrogen_dioxide",
    ]


def load_data(feature_cols: list) -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    log.info("Loaded forecast features: %d rows", len(df))
    for col in feature_cols:
        if col not in df.columns:
            log.warning("Feature '%s' missing — filling with 0", col)
            df[col] = 0.0
    return df


def predict(model, df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
    X = df[feature_cols]
    predictions   = model.predict(X)
    probabilities = model.predict_proba(X)
    class_labels  = list(model.classes_)

    df = df.copy()
    df["predicted_category"] = predictions
    df["confidence"]         = probabilities.max(axis=1).round(4)

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


def get_connection() -> pyodbc.Connection:
    server   = os.environ["SQL_SERVER"]
    database = os.environ.get("SQL_DATABASE", "AetherDW_V0")
    driver   = os.environ.get("SQL_DRIVER", "ODBC Driver 17 for SQL Server")
    return pyodbc.connect(
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
    )


# ── FIXED UPSERT: now includes all 4 new v2 columns ──────────────────────────
UPSERT_SQL = """
MERGE dbo.ForecastPredictions AS target
USING (VALUES (?, ?, ?, ?)) AS src
    (forecast_date, forecast_horizon, model_version, generated_at)
ON  target.forecast_date    = src.forecast_date
AND target.forecast_horizon = src.forecast_horizon
AND target.model_version    = src.model_version
WHEN MATCHED THEN UPDATE SET
    generated_at        = ?,
    temperature         = ?, humidity           = ?, wind              = ?,
    pressure            = ?, cloud_cover        = ?,
    pm25                = ?, pm10               = ?, aqi               = ?,
    ozone               = ?, nitrogen_dioxide   = ?, sulphur_dioxide   = ?,
    heat_index          = ?, pollution_level    = ?,
    respiratory_stress  = ?, uv_risk            = ?,
    predicted_category  = ?, confidence         = ?,
    prob_safe           = ?, prob_moderate      = ?, prob_high_resp    = ?,
    prob_mask           = ?, prob_avoid         = ?,
    temp_range          = ?, heat_stress_peak   = ?,
    dust_risk_index     = ?, rain_wash_effect   = ?
WHEN NOT MATCHED THEN INSERT (
    forecast_date, forecast_horizon, generated_at, model_version,
    temperature, humidity, wind, pressure, cloud_cover,
    pm25, pm10, aqi, ozone, nitrogen_dioxide, sulphur_dioxide,
    heat_index, pollution_level, respiratory_stress, uv_risk,
    predicted_category, confidence,
    prob_safe, prob_moderate, prob_high_resp, prob_mask, prob_avoid,
    temp_range, heat_stress_peak, dust_risk_index, rain_wash_effect
) VALUES (
    ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?,
    ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?
);
"""


def g(row, col):
    """Safe getter — returns None instead of NaN."""
    val = row.get(col)
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def upsert(df: pd.DataFrame) -> None:
    conn   = get_connection()
    cursor = conn.cursor()
    now    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows_affected = 0

    for _, row in df.iterrows():
        match  = (str(row["date"]), int(row["horizon"]), MODEL_VERSION, now)

        update = (
            now,
            g(row,"temperature"), g(row,"humidity"),         g(row,"wind"),
            g(row,"pressure"),    g(row,"cloud_cover"),
            g(row,"pm25"),        g(row,"pm10"),              g(row,"aqi"),
            g(row,"ozone"),       g(row,"nitrogen_dioxide"),  g(row,"sulphur_dioxide"),
            g(row,"heat_index"),  g(row,"pollution_level"),
            g(row,"respiratory_stress"), g(row,"uv_risk"),
            row["predicted_category"],   row["confidence"],
            g(row,"prob_safe"),   g(row,"prob_moderate"),     g(row,"prob_high_resp"),
            g(row,"prob_mask"),   g(row,"prob_avoid"),
            g(row,"temp_range"),  g(row,"heat_stress_peak"),
            g(row,"dust_risk_index"), g(row,"rain_wash_effect"),
        )

        insert = (
            str(row["date"]), int(row["horizon"]), now, MODEL_VERSION,
            g(row,"temperature"), g(row,"humidity"),         g(row,"wind"),
            g(row,"pressure"),    g(row,"cloud_cover"),
            g(row,"pm25"),        g(row,"pm10"),              g(row,"aqi"),
            g(row,"ozone"),       g(row,"nitrogen_dioxide"),  g(row,"sulphur_dioxide"),
            g(row,"heat_index"),  g(row,"pollution_level"),
            g(row,"respiratory_stress"), g(row,"uv_risk"),
            row["predicted_category"],   row["confidence"],
            g(row,"prob_safe"),   g(row,"prob_moderate"),     g(row,"prob_high_resp"),
            g(row,"prob_mask"),   g(row,"prob_avoid"),
            g(row,"temp_range"),  g(row,"heat_stress_peak"),
            g(row,"dust_risk_index"), g(row,"rain_wash_effect"),
        )

        cursor.execute(UPSERT_SQL, match + update + insert)
        rows_affected += cursor.rowcount

    conn.commit()
    conn.close()
    log.info("Upserted %d forecast rows → ForecastPredictions", rows_affected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    model        = load_model()
    feature_cols = load_feature_cols()
    data         = load_data(feature_cols)
    results      = predict(model, data, feature_cols)

    if args.dry_run:
        log.info("Dry run — skipping database write")
        print(results[["date","horizon","predicted_category","confidence"]].to_string())
        return

    upsert(results)
    log.info("Forecast pipeline complete")


if __name__ == "__main__":
    main()