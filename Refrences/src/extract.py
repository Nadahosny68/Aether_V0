import requests
import json
import sys
import os
from config import Config
from utils import setup_logger

# Initialize logger
logger = setup_logger(__name__)

def fetch_weather_data(city, start_date, end_date):
    """
    Fetch weather data for a given location and date range from the Visual Crossing API.

    Parameters:
        city (str): City for which the weather data is needed.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        dict: The weather data as a Python dictionary.
    """
    # API request URL
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}/{start_date}/{end_date}?unitGroup=metric&include=days&key={Config.VISUALCROSSING_API_KEY}&contentType=json"

    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for any error response

        # Parse the response JSON
        weather_data = response.json()
        return weather_data

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        sys.exit(1)

    except Exception as err:
        logger.error(f"An error occurred: {err}")
        sys.exit(1)

def fetch_historical_air_quality_data(city, state, country, start_date, end_date):
    """
    Fetch historical air quality data for a given location and date range from the AirVisual API.

    Parameters:
        city (str): The city for which the air quality data is needed.
        state (str): The state or region.
        country (str): The country.
        start_date (str): The start date in YYYY-MM-DD format.
        end_date (str): The end date in YYYY-MM-DD format.

    Returns:
        dict: The air quality data as a Python dictionary.
    """
    url = (f"https://api.airvisual.com/v2/history?city={city}&state={state}&country={country}"
           f"&start={start_date}&end={end_date}&key={Config.AIRVISUAL_API_KEY}")

    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for any error response

        # Parse the response JSON
        air_quality_data = response.json()
        return air_quality_data

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        sys.exit(1)

    except Exception as err:
        logger.error(f"An error occurred: {err}")
        sys.exit(1)

def main():
    city = Config.DEFAULT_CITY
    state = Config.DEFAULT_STATE
    country = Config.DEFAULT_COUNTRY
    start_date = Config.DEFAULT_START_DATE
    end_date = Config.DEFAULT_END_DATE

    logger.info(f"Fetching weather data for {city} from {start_date} to {end_date}...")
    weather_data = fetch_weather_data(city, start_date, end_date)

    logger.info(f"Fetching historical air quality data for {city}, {state}, {country} from {start_date} to {end_date}...")
    air_quality_data = fetch_historical_air_quality_data(city, state, country, start_date, end_date)

    # Save the raw data to a file
    with open("weather_data.json", "w") as file:
        json.dump(weather_data, file, indent=4)
    logger.info("Weather data saved to weather_data.json")

    with open("historical_air_quality_data.json", "w") as file:
        json.dump(air_quality_data, file, indent=4)
    logger.info("Historical air quality data saved to historical_air_quality_data.json")

if __name__ == "__main__":
    main()