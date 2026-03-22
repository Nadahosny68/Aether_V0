import requests
import json
import os
import logging
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PollutionFetcher")

CITY  = "Cairo"
TOKEN = "16491ebad3d05b7e3f4f0f5a3d5e316bd5cb6f39"
URL   = f"https://api.waqi.info/feed/cairo/?token={TOKEN}"

def fetch_pollution():
    logger.info(f"Fetching pollution data for {CITY}...")

    try:
        response = requests.get(URL, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise

    data = response.json()

    if data.get("status") != "ok":
        logger.error(f"WAQI returned status: {data.get('status')}")
        raise Exception("WAQI API returned non-ok status")

    d = data["data"]
    iaqi = d.get("iaqi", {})

    record = {
        "fetched_at": datetime.utcnow().isoformat(),
        "date":       datetime.utcnow().strftime("%Y-%m-%d"),
        "city":       CITY,
        "station":    d.get("city", {}).get("name", "Cairo"),
        "aqi":        d.get("aqi"),
        "pm25":       iaqi.get("pm25", {}).get("v"),
        "pm10":       iaqi.get("pm10", {}).get("v"),
        "temperature":iaqi.get("t",    {}).get("v"),
        "humidity":   iaqi.get("h",    {}).get("v"),
        "wind":       iaqi.get("w",    {}).get("v"),
    }

    # Save raw JSON
    raw_dir  = os.path.join(ROOT, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    filename = f"pollution_api_{datetime.utcnow().strftime('%Y%m%d')}.json"
    filepath = os.path.join(raw_dir, filename)

    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)

    logger.info(f"Pollution data saved to {filename}")
    logger.info(f"  AQI:  {record['aqi']}")
    logger.info(f"  PM2.5: {record['pm25']}")
    logger.info(f"  PM10:  {record['pm10']}")

    return record

if __name__ == "__main__":
    fetch_pollution()



# Get your free WAQI token, paste it in, then run:
# python pipelines/ingestion/fetch_pollution_api.py