import pandas as pd
import os

# Paths to raw data
weather_path = r"D:\Aether\Aether_V0\data\raw\weather_data.csv"
pollution_path = r"D:\Aether\Aether_V0\data\raw\air_pollution_data.csv"

print("Loading datasets...")


# Load datasets
weather_df = pd.read_csv(weather_path)
pollution_df = pd.read_csv(pollution_path)

print("\nWeather Dataset Shape:")
print(weather_df.shape)

print("\nPollution Dataset Shape:")
print(pollution_df.shape)

print("\nWeather Columns:")
print(weather_df.columns)

print("\nPollution Columns:")
print(pollution_df.columns)

print("\nPreview Weather Data:")
print(weather_df.head())

print("\nPreview Pollution Data:")
print(pollution_df.head())