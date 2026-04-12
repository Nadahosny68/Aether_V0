"""
ML/inference/predict_forecast.py
─────────────────────────────────
Loads the trained model and runs inference on forecast_features.csv,
then upserts results to ForecastPredictions.

New in v2: loads the saved feature_columns.pkl so the feature list
always matches whatever was used at training time — no manual sync needed.
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
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    log.info("Model loaded: %s", MODEL_PATH)
    return model


def load_feature_cols() -> list:
    """
    Load the exact feature list saved during training.
    This guarantees inference always uses the same columns as training,
    even after future feature additions.
    """
    if not os.path.exists(FEATURES_PATH):
        # Fallback to base features if file doesn't exist (pre-v2 model)
        log.warning(
            "feature_columns.pkl not found — using base feature list. "
            "Re-run train_risk_model.py to generate it."
        )
        return [
            "temperature", "humidity", "wind", "heat_index",
            "pm25", "pm10", "aqi", "pollution_level",
            "respiratory_stress", "uv_risk",
            "pressure", "ozone", "nitrogen_dioxide",
        ]
    with open(FEATURES_PATH, "rb") as f:
        cols = pickle.load(f)
    log.info("Feature columns loaded: %s", cols)
    return cols


def load_data(feature_cols: list) -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Forecast features not found: {DATA_PATH}\n"
            "Run feature_engineering_forecast.py first."
        )
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    log.info("Loaded forecast features: %d rows", len(df))

    # Fill any missing new feature columns with 0
    # (handles case where forecast data doesn't have all columns)
    for col in feature_cols:
        if col not in df.columns:
            log.warning("Feature '%s' missing from forecast data — filling with 0", col)
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
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


UPSERT_SQL = """
MERGE dbo.ForecastPredictions AS target
USING (VALUES (?, ?, ?, ?)) AS src
    (forecast_date, forecast_horizon, model_version, generated_at)
ON  target.forecast_date    = src.forecast_date
AND target.forecast_horizon = src.forecast_horizon
AND target.model_version    = src.model_version
WHEN MATCHED THEN UPDATE SET
    generated_at       = ?,
    temperature        = ?, humidity          = ?, wind             = ?,
    pressure           = ?, cloud_cover       = ?,
    pm25               = ?, pm10              = ?, aqi              = ?,
    ozone              = ?, nitrogen_dioxide  = ?, sulphur_dioxide  = ?,
    heat_index         = ?, pollution_level   = ?,
    respiratory_stress = ?, uv_risk           = ?,
    predicted_category = ?, confidence        = ?,
    prob_safe          = ?, prob_moderate     = ?, prob_high_resp   = ?,
    prob_mask          = ?, prob_avoid        = ?
WHEN NOT MATCHED THEN INSERT (
    forecast_date, forecast_horizon, generated_at, model_version,
    temperature, humidity, wind, pressure, cloud_cover,
    pm25, pm10, aqi, ozone, nitrogen_dioxide, sulphur_dioxide,
    heat_index, pollution_level, respiratory_stress, uv_risk,
    predicted_category, confidence,
    prob_safe, prob_moderate, prob_high_resp, prob_mask, prob_avoid
) VALUES (
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
        match  = (str(row["date"]), int(row["horizon"]), MODEL_VERSION, now)
        update = (
            now,
            row.get("temperature"), row.get("humidity"),         row.get("wind"),
            row.get("pressure"),    row.get("cloud_cover"),
            row.get("pm25"),        row.get("pm10"),              row.get("aqi"),
            row.get("ozone"),       row.get("nitrogen_dioxide"),  row.get("sulphur_dioxide"),
            row.get("heat_index"),  row.get("pollution_level"),
            row.get("respiratory_stress"), row.get("uv_risk"),
            row["predicted_category"],     row["confidence"],
            row.get("prob_safe"),   row.get("prob_moderate"),     row.get("prob_high_resp"),
            row.get("prob_mask"),   row.get("prob_avoid"),
        )
        insert = (
            str(row["date"]), int(row["horizon"]), now, MODEL_VERSION,
            row.get("temperature"), row.get("humidity"),         row.get("wind"),
            row.get("pressure"),    row.get("cloud_cover"),
            row.get("pm25"),        row.get("pm10"),              row.get("aqi"),
            row.get("ozone"),       row.get("nitrogen_dioxide"),  row.get("sulphur_dioxide"),
            row.get("heat_index"),  row.get("pollution_level"),
            row.get("respiratory_stress"), row.get("uv_risk"),
            row["predicted_category"],     row["confidence"],
            row.get("prob_safe"),   row.get("prob_moderate"),     row.get("prob_high_resp"),
            row.get("prob_mask"),   row.get("prob_avoid"),
        )
        cursor.execute(UPSERT_SQL, match + update + insert)
        rows_affected += cursor.rowcount

    conn.commit()
    conn.close()
    log.info("Upserted %d forecast rows → ForecastPredictions", rows_affected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print predictions without writing to database")
    args = parser.parse_args()

    model        = load_model()
    feature_cols = load_feature_cols()
    data         = load_data(feature_cols)
    results      = predict(model, data, feature_cols)

    if args.dry_run:
        log.info("Dry run — skipping database write")
        print(results[["date", "horizon", "predicted_category", "confidence"]].to_string())
        return

    upsert(results)
    log.info("Forecast pipeline complete")


if __name__ == "__main__":
    main()