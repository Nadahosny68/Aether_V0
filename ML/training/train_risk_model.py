"""
ML/training/train_risk_model.py
────────────────────────────────
Trains the Random Forest classifier on EnvironmentalFeatures.
Reads from SQL Server after the full ETL pipeline has run.

New in v2: includes 4 new features — temp_range, heat_stress_peak,
dust_risk_index, rain_wash_effect — derived from max/min weather columns.
Only uses features that actually exist in the table (safe fallback).
"""

import os
import pickle
import pandas as pd
import pyodbc
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

print("Loading data from SQL...")
conn = pyodbc.connect(
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-Q5KEU1E;"
    "DATABASE=AetherDW_V0;"
    "Trusted_Connection=yes;",
    timeout=30
)
df = pd.read_sql("SELECT * FROM EnvironmentalFeatures", conn)
conn.close()
print(f"  Rows loaded: {len(df)}")
print(f"  Columns available: {list(df.columns)}")

# ── Feature list ───────────────────────────────────────────────────────────────
# Original features (always present)
FEATURES_BASE = [
    "temperature", "humidity", "wind", "heat_index",
    "pm25", "pm10", "aqi", "pollution_level",
    "respiratory_stress", "uv_risk",
    "pressure", "ozone", "nitrogen_dioxide",
]

# New v2 features (only used if column exists in the table)
# Run the full pipeline first (data_cleaning → feature_engineering → SSIS)
# to populate these columns before training.
FEATURES_NEW = [
    "temp_range",        # diurnal temperature swing
    "heat_stress_peak",  # apparent_temp_max — worst-case felt heat
    "dust_risk_index",   # wind_max × dryness — Cairo dust storm proxy
    "rain_wash_effect",  # precipitation mm — rain reduces effective pollution
]

TARGET = "health_category"

# Only use new features if they exist in the loaded data
FEATURES = FEATURES_BASE + [f for f in FEATURES_NEW if f in df.columns]

new_found = [f for f in FEATURES_NEW if f in df.columns]
new_missing = [f for f in FEATURES_NEW if f not in df.columns]
print(f"\n  New features found:   {new_found}")
if new_missing:
    print(f"  New features missing: {new_missing}")
    print(f"  → Re-run data_cleaning.py + feature_engineering.py + SSIS to populate them")

df = df.dropna(subset=FEATURES + [TARGET])
print(f"\n  Rows after dropping nulls: {len(df)}")
print(f"  Health category distribution:")
print(df[TARGET].value_counts().to_string())

X = df[FEATURES]
y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n  Training rows: {len(X_train)}")
print(f"  Testing rows:  {len(X_test)}")
print(f"  Total features: {len(FEATURES)}")

print("\nTraining Random Forest model...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    random_state=42,
    class_weight="balanced",
)
model.fit(X_train, y_train)
print("Model training completed.")

predictions = model.predict(X_test)
print("\nModel Performance:")
print(classification_report(y_test, predictions))

importance = pd.Series(
    model.feature_importances_, index=FEATURES
).sort_values(ascending=False)
print("\nFeature Importance:")
print(importance.to_string())

# Save the feature list alongside the model so inference scripts
# always use exactly the same columns
model_path   = os.path.join(ROOT, "ML", "models", "environmental_risk_model.pkl")
features_path = os.path.join(ROOT, "ML", "models", "feature_columns.pkl")

os.makedirs(os.path.dirname(model_path), exist_ok=True)

with open(model_path, "wb") as f:
    pickle.dump(model, f)
print(f"\nModel saved to:    {model_path}")

with open(features_path, "wb") as f:
    pickle.dump(FEATURES, f)
print(f"Features saved to: {features_path}")
print(f"Feature columns:   {FEATURES}")