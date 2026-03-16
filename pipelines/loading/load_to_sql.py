import pandas as pd
import pyodbc

print("Starting SQL load pipeline...")

# Database connection
conn = pyodbc.connect(
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-Q5KEU1E;"
    "DATABASE=AetherDW;"
    "Trusted_Connection=yes;"
)

cursor = conn.cursor()

# Load processed data
weather = pd.read_csv("data/processed/weather_features.csv")
pollution = pd.read_csv("data/processed/pollution_features.csv")

# -------------------------
# Insert Weather Data
# -------------------------

for _, row in weather.iterrows():

    cursor.execute("""
        INSERT INTO WeatherMetrics
        (date, temperature, humidity, wind, heat_index)
        VALUES (?, ?, ?, ?, ?)
    """,
    row.get('date'),
    row.get('temperature'),
    row.get('humidity'),
    row.get('wind'),
    row.get('heat_index')
    )

conn.commit()

print("Weather data inserted.")

# -------------------------
# Insert Pollution Data
# -------------------------

for _, row in pollution.iterrows():

    cursor.execute("""
        INSERT INTO PollutionMetrics
        (date, pm25, pm10, aqi, pollution_level)
        VALUES (?, ?, ?, ?, ?)
    """,
    row.get('date'),
    row.get('pm25'),
    row.get('pm10'),
    row.get('aqi'),
    row.get('pollution_level')
    )

conn.commit()

print("Pollution data inserted.")

cursor.close()
conn.close()

print("SQL loading completed.")