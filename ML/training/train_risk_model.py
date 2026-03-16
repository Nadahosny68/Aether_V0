import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import pyodbc
import joblib

print("Loading data from SQL...")

conn = pyodbc.connect(
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-Q5KEU1E;"
    "DATABASE=AetherDW;"
    "Trusted_Connection=yes;"
)

weather = pd.read_sql("SELECT * FROM WeatherMetrics", conn)
pollution = pd.read_sql("SELECT * FROM PollutionMetrics", conn)

conn.close()

# -----------------------------
# Merge datasets
# -----------------------------

data = pd.merge(weather, pollution, on="date")

# -----------------------------
# Create Risk Label
# -----------------------------

def classify_risk(row):
    
    if row["aqi"] > 150 or row["pm25"] > 100:
        return "High"
    
    elif row["aqi"] > 80 or row["pm25"] > 50:
        return "Moderate"
    
    else:
        return "Low"

data["risk_level"] = data.apply(classify_risk, axis=1)

print("Risk labels created.")

# -----------------------------
# Prepare features
# -----------------------------

features = [
    "temperature",
    "humidity",
    "wind",
    "heat_index",
    "pm25",
    "pm10",
    "aqi",
    "pollution_level"
]

X = data[features]
y = data["risk_level"]

# -----------------------------
# Train/Test Split
# -----------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# -----------------------------
# Train Model
# -----------------------------

model = RandomForestClassifier(n_estimators=100)

model.fit(X_train, y_train)

print("Model training completed.")

# -----------------------------
# Evaluate Model
# -----------------------------

predictions = model.predict(X_test)

print("\nModel Performance:")
print(classification_report(y_test, predictions))

# -----------------------------
# Save Model
# -----------------------------

joblib.dump(model, "ml/models/environmental_risk_model.pkl")

print("\nModel saved.")