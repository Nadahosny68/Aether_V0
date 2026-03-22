import pandas as pd
import pyodbc
import joblib
import os
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SERVER   = "DESKTOP-Q5KEU1E"
DATABASE = "AetherDW_V0"

FEATURES = [
    "temperature",
    "humidity",
    "wind",
    "heat_index",
    "pm25",
    "pm10",
    "aqi",
    "pollution_level",
    "respiratory_stress",
    "uv_risk",
    "pressure",
    "ozone",
    "nitrogen_dioxide",
]

MODEL_VERSION = "v2.0"

print("Loading trained model...")
model_path = os.path.join(ROOT, "ML", "models", "environmental_risk_model.pkl")
model = joblib.load(model_path)

print("Connecting to database...")
conn = pyodbc.connect(
    f"DRIVER={{SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)

# ── Load data for prediction ───────────────────────────────────────────────
# Only predict on dates not already in RiskPredictions
query = """
    SELECT ef.*
    FROM EnvironmentalFeatures ef
    WHERE ef.date IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM RiskPredictions rp
        WHERE rp.date = ef.date
    )
"""

df = pd.read_sql(query, conn)
print(f"  Rows needing prediction: {len(df)}")

if len(df) == 0:
    print("  No new rows to predict. All dates already have predictions.")
    conn.close()
    exit()

# ── Fill nulls in features with 0 for prediction ─────────────────────────
for col in FEATURES:
    if col in df.columns:
        df[col] = df[col].fillna(0)
    else:
        df[col] = 0

X = df[FEATURES]

# ── Generate predictions ───────────────────────────────────────────────────
print("Generating predictions...")
df["health_category"] = model.predict(X)

print(f"\n  Prediction distribution:")
print(df["health_category"].value_counts().to_string())

# ── Insert into RiskPredictions ────────────────────────────────────────────
print("\nInserting predictions into RiskPredictions...")
cursor = conn.cursor()

inserted = 0
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO RiskPredictions
            (date, temperature, humidity, wind, heat_index,
            pm25, pm10, aqi, pollution_level,
            respiratory_stress, uv_risk,
            health_category, model_version, predicted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    row.get("date"),
    row.get("temperature"),
    row.get("humidity"),
    row.get("wind"),
    row.get("heat_index"),
    row.get("pm25"),
    row.get("pm10"),
    row.get("aqi"),
    row.get("pollution_level"),
    row.get("respiratory_stress"),
    row.get("uv_risk"),
    row.get("health_category"),
    MODEL_VERSION,
    datetime.now()
    )
    inserted += 1

conn.commit()
cursor.close()
conn.close()

print(f"  {inserted} predictions inserted.")
print("Prediction pipeline completed.")




# Two things worth noting about these changes:
# `class_weight="balanced"` in the RandomForest handles the case where some health categories appear much more often than others. 
# Without it the model would be biased toward the most common category and rarely predict rare ones like "Avoid Outdoor Activity Day".

# The prediction query in `predict_risk.py` uses `NOT EXISTS` — same pattern as DimDate — so running it multiple times never creates duplicates. 
# It only predicts dates that don't already have a prediction.

# Run training first:
# python ML/training/train_risk_model.py