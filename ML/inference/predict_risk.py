import pandas as pd
import pyodbc
import joblib

print("Loading trained model...")

model = joblib.load("ml/models/environmental_risk_model.pkl")

print("Connecting to database...")

conn = pyodbc.connect(
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-Q5KEU1E;"
    "DATABASE=AetherDW;"
    "Trusted_Connection=yes;"
)

# Load latest data
query = """
SELECT
    w.date,
    w.temperature,
    w.humidity,
    w.wind,
    w.heat_index,
    p.pm25,
    p.pm10,
    p.aqi,
    p.pollution_level
FROM WeatherMetrics w
JOIN PollutionMetrics p
ON w.date = p.date
"""

data = pd.read_sql(query, conn)

print("Data loaded for prediction.")

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

print("Generating predictions...")

predictions = model.predict(X)

data["predicted_risk"] = predictions

cursor = conn.cursor()

# Insert predictions
for _, row in data.iterrows():

    cursor.execute("""
        INSERT INTO RiskPredictions
        (date, temperature, humidity, wind, heat_index,
         pm25, pm10, aqi, pollution_level, predicted_risk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    row["date"],
    row["temperature"],
    row["humidity"],
    row["wind"],
    row["heat_index"],
    row["pm25"],
    row["pm10"],
    row["aqi"],
    row["pollution_level"],
    row["predicted_risk"]
    )

conn.commit()

print("Predictions inserted into database.")

cursor.close()
conn.close()