import requests
import json
import os
import time
import logging
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WeatherFetcher")

API_KEY = "093322d3ab292dee09c09f0639d1ef17"
CITY    = "Cairo"
COUNTRY = "EG"
UNITS   = "metric"
URL     = (
    f"https://api.openweathermap.org/data/2.5/weather"
    f"?q={CITY},{COUNTRY}&appid={API_KEY}&units={UNITS}"
)

def fetch_weather():
    logger.info(f"Fetching weather data for {CITY}...")

    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise

    data = response.json()

    # Extract what Aether needs
    record = {
        "fetched_at":  datetime.utcnow().isoformat(),
        "city":        data.get("name"),
        "date":        datetime.utcnow().strftime("%Y-%m-%d"),
        "temperature": data["main"]["temp"],
        "humidity":    data["main"]["humidity"],
        "wind":        data["wind"]["speed"],
        "pressure":    data["main"]["pressure"],
        "weather":     data["weather"][0]["description"]
    }

    # Save raw JSON
    raw_dir  = os.path.join(ROOT, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    filename = f"weather_api_{datetime.utcnow().strftime('%Y%m%d')}.json"
    filepath = os.path.join(raw_dir, filename)

    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)

    logger.info(f"Weather data saved to {filename}")
    logger.info(f"  Temperature: {record['temperature']}°C")
    logger.info(f"  Humidity:    {record['humidity']}%")
    logger.info(f"  Wind:        {record['wind']} m/s")

    return record

if __name__ == "__main__":
    fetch_weather()
    
    
    

# Now test both individually:
# python pipelines/ingestion/fetch_weather_api.py