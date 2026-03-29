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
    "Trusted_Connection=yes;"
)
df = pd.read_sql("SELECT * FROM EnvironmentalFeatures", conn)
conn.close()
print(f"  Rows loaded: {len(df)}")

FEATURES = [
    "temperature", "humidity", "wind", "heat_index",
    "pm25", "pm10", "aqi", "pollution_level",
    "respiratory_stress", "uv_risk",
    "pressure", "ozone", "nitrogen_dioxide",
]
TARGET = "health_category"

df = df.dropna(subset=FEATURES + [TARGET])
print(f"  Rows after dropping nulls: {len(df)}")
print(f"\n  Health category distribution:")
print(df[TARGET].value_counts().to_string())

X = df[FEATURES]
y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n  Training rows: {len(X_train)}")
print(f"  Testing rows:  {len(X_test)}")

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

model_path = os.path.join(ROOT, "ML", "models", "environmental_risk_model.pkl")
os.makedirs(os.path.dirname(model_path), exist_ok=True)
with open(model_path, "wb") as f:
    pickle.dump(model, f)
print(f"\nModel saved to: {model_path}")