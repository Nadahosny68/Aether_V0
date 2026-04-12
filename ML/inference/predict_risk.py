"""
ML/inference/predict_risk.py
──────────────────────────────
Predicts health category for new rows in EnvironmentalFeatures
and inserts results into RiskPredictions.

✔ Uses correct feature list from training
✔ Handles missing columns safely
✔ Inserts NEW engineered features
✔ Optional evaluation (if ground truth exists)
"""

import os
import sys
import pickle
import pandas as pd
import pyodbc
from datetime import datetime
from dotenv import load_dotenv
from sklearn.metrics import classification_report

# ── Setup ──────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

SERVER   = os.environ.get("SQL_SERVER",   "DESKTOP-Q5KEU1E")
DATABASE = os.environ.get("SQL_DATABASE", "AetherDW_V0")

MODEL_PATH    = os.path.join(ROOT, "ML", "models", "environmental_risk_model.pkl")
FEATURES_PATH = os.path.join(ROOT, "ML", "models", "feature_columns.pkl")
MODEL_VERSION = "v3.0"   # 🔥 updated version

# ── Load model ─────────────────────────────────────────────────────────────
print("Loading trained model...")
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

# ── Load feature columns ───────────────────────────────────────────────────
if os.path.exists(FEATURES_PATH):
    with open(FEATURES_PATH, "rb") as f:
        FEATURES = pickle.load(f)
    print(f"Feature columns loaded: {FEATURES}")
else:
    FEATURES = [
        "temperature", "humidity", "wind", "heat_index",
        "pm25", "pm10", "aqi", "pollution_level",
        "respiratory_stress", "uv_risk",
        "pressure", "ozone", "nitrogen_dioxide",
        # NEW features fallback
        "temp_range", "heat_stress_peak",
        "dust_risk_index", "rain_wash_effect"
    ]
    print("⚠️ feature_columns.pkl not found, using fallback features")

# ── Connect DB ─────────────────────────────────────────────────────────────
print("Connecting to database...")
conn = pyodbc.connect(
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-Q5KEU1E;"
    "DATABASE=AetherDW_V0;"
    "Trusted_Connection=yes;",
    timeout=30
)

# ── Load new rows only ─────────────────────────────────────────────────────
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

print(f"Rows needing prediction: {len(df)}")

if len(df) == 0:
    print("No new rows to predict.")
    conn.close()
    exit()

# ── Prepare features safely ────────────────────────────────────────────────
for col in FEATURES:
    if col in df.columns:
        df[col] = df[col].fillna(0)
    else:
        print(f"⚠️ Missing column '{col}' → filled with 0")
        df[col] = 0

X = df[FEATURES]

# ── Predict ────────────────────────────────────────────────────────────────
print("Generating predictions...")
df["health_category"] = model.predict(X)

print("\nPrediction distribution:")
print(df["health_category"].value_counts().to_string())

# ── OPTIONAL EVALUATION (only if ground truth exists) ──────────────────────
if "health_category_actual" in df.columns:
    print("\nEvaluation:")
    print(classification_report(df["health_category_actual"], df["health_category"]))

# ── Insert into DB ─────────────────────────────────────────────────────────
print("\nInserting predictions...")
cursor = conn.cursor()
inserted = 0

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO RiskPredictions
            (date, temperature, humidity, wind, heat_index,
            pm25, pm10, aqi, pollution_level,
            respiratory_stress, uv_risk,
            temp_range, heat_stress_peak, dust_risk_index, rain_wash_effect,
            health_category, model_version, predicted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        row.get("temp_range"),
        row.get("heat_stress_peak"),
        row.get("dust_risk_index"),
        row.get("rain_wash_effect"),
        row.get("health_category"),
        MODEL_VERSION,
        datetime.now()
    )
    inserted += 1

conn.commit()
cursor.close()
conn.close()

print(f"\nInserted {inserted} predictions.")
print("Prediction pipeline completed.")