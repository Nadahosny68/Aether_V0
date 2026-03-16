import pandas as pd

print("Starting feature engineering...")

# -----------------------------
# Load CLEAN datasets
# -----------------------------

weather = pd.read_csv("data/staging/weather_clean.csv")
pollution = pd.read_csv("data/staging/pollution_clean.csv")

# -----------------------------
# Standardize Weather Columns
# -----------------------------

weather = weather.rename(columns={
    "Formatted Date": "date",
    "Temperature (C)": "temperature",
    "Humidity": "humidity",
    "Wind Speed (km/h)": "wind"
})

# Convert date safely
weather["date"] = pd.to_datetime(weather["date"], errors="coerce", utc=True)
weather["date"] = weather["date"].dt.date

# Keep only needed columns
weather = weather[["date", "temperature", "humidity", "wind"]]

# -----------------------------
# Heat Index Calculation
# -----------------------------

weather["heat_index"] = (
    weather["temperature"]
    + (0.33 * weather["humidity"])
    - (0.70 * weather["wind"])
)

print("Heat Index feature created.")

# -----------------------------
# Standardize Pollution Columns
# -----------------------------

pollution = pollution.rename(columns={
    "Date": "date",
    "PM2.5": "pm25",
    "PM10": "pm10",
    "AQI": "aqi"
})

pollution["date"] = pd.to_datetime(pollution["date"], errors="coerce")
pollution["date"] = pollution["date"].dt.date

pollution = pollution[["date", "pm25", "pm10", "aqi"]]

# -----------------------------
# Pollution Level
# -----------------------------

pollution["pollution_level"] = (
    pollution["pm25"] * 0.5
    + pollution["pm10"] * 0.3
    + pollution["aqi"] * 0.2
)

print("Pollution Level feature created.")

# -----------------------------
# Save processed datasets
# -----------------------------

weather.to_csv("data/processed/weather_features.csv", index=False)
pollution.to_csv("data/processed/pollution_features.csv", index=False)

print("Feature engineering completed.")