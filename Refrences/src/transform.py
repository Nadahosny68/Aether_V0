import pandas as pd
import json
import sys
from config import Config
from utils import setup_logger, clean_column_names

# Initialize logger
logger = setup_logger(__name__)

def load_data(file_name="weather_data.json"):
    """
    Load weather data from a JSON file.

    Parameters:
        file_name (str): The name of the file to load the data from.

    Returns:
        dict: The weather data as a Python dictionary.
    """
    try:
        with open(file_name, "r") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        logger.error(f"File {file_name} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from the file.")
        sys.exit(1)

def transform_data(weather_data):
    """
    Transform the raw weather data into a structured DataFrame.

    Parameters:
        weather_data (dict): The raw weather data.

    Returns:
        pd.DataFrame: The transformed weather data in a DataFrame.
    """
    try:
        # Extract relevant data
        records = weather_data.get("days", [])
        df = pd.DataFrame(records)

        # Select and rename columns as needed
        df = df[["datetime", "temp", "feelslike", "humidity", "precip", "windspeed"]]
        df.columns = ["date", "temperature", "feels_like", "humidity", "precipitation", "wind_speed"]

        # Convert data types
        df["date"] = pd.to_datetime(df["date"])
        df["temperature"] = pd.to_numeric(df["temperature"], errors='coerce')
        df["feels_like"] = pd.to_numeric(df["feels_like"], errors='coerce')
        df["humidity"] = pd.to_numeric(df["humidity"], errors='coerce')
        df["precipitation"] = pd.to_numeric(df["precipitation"], errors='coerce')
        df["wind_speed"] = pd.to_numeric(df["wind_speed"], errors='coerce')

        # Handle missing values
        df.fillna(method='ffill', inplace=True)  # Forward fill missing values
        df.dropna(inplace=True)  # Drop any remaining missing values

        # Clean column names
        df = clean_column_names(df)

        return df

    except KeyError as e:
        logger.error(f"Missing expected key in data: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred during data transformation: {e}")
        sys.exit(1)

def main():
    # Load the raw data
    raw_data = load_data("weather_data.json")
    
    # Transform the data
    transformed_data = transform_data(raw_data)
    
    # Save the transformed data
    transformed_data.to_csv("transformed_weather_data.csv", index=False)
    logger.info("Transformed data saved to transformed_weather_data.csv")

if __name__ == "__main__":
    main()
