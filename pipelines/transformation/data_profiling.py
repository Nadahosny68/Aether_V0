import pandas as pd

# Paths
weather_path = r"D:\Aether\Aether_V0\data\raw\cairo_weather_historical.csv"
pollution_path = r"D:\Aether\Aether_V0\data\raw\cairo_airquality_historical.csv"

print("Loading datasets...")

weather_df = pd.read_csv(weather_path)
pollution_df = pd.read_csv(pollution_path)

# -----------------------------
# Weather Dataset Profiling
# -----------------------------

print("\n==============================")
print("WEATHER DATA PROFILING")
print("==============================")

print("\nDataset Shape:")
print(weather_df.shape)

print("\nColumn Names:")
print(weather_df.columns)

print("\nData Types:")
print(weather_df.dtypes)

print("\nMissing Values:")
print(weather_df.isnull().sum())

print("\nSummary Statistics:")
print(weather_df.describe())

# -----------------------------
# Pollution Dataset Profiling
# -----------------------------

print("\n==============================")
print("POLLUTION DATA PROFILING")
print("==============================")

print("\nDataset Shape:")
print(pollution_df.shape)

print("\nColumn Names:")
print(pollution_df.columns)

print("\nData Types:")
print(pollution_df.dtypes)

print("\nMissing Values:")
print(pollution_df.isnull().sum())

print("\nSummary Statistics:")
print(pollution_df.describe())