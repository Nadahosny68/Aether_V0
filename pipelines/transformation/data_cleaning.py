import pandas as pd

# Paths
weather_path = r"D:\Aether\Aether_V0\data\raw\weather_data.csv"
pollution_path = r"D:\Aether\Aether_V0\data\raw\air_pollution_data.csv"

print("Cleaning datasets...")

weather_df = pd.read_csv(weather_path)
pollution_df = pd.read_csv(pollution_path)

# ---------------------------
# Weather Cleaning
# ---------------------------

weather_df = weather_df.drop_duplicates()

weather_df = weather_df.dropna()

# Convert date column if exists
if 'date' in weather_df.columns:
    weather_df['date'] = pd.to_datetime(weather_df['date'])

# ---------------------------
# Pollution Cleaning
# ---------------------------

pollution_df = pollution_df.drop_duplicates()

pollution_df = pollution_df.dropna()

# ---------------------------
# Save Clean Data
# ---------------------------

weather_df.to_csv("data\staging\weather_clean.csv", index=False)

pollution_df.to_csv("data\staging\pollution_clean.csv", index=False)

print("\nCleaning completed.")
print("Files saved in data/staging/")