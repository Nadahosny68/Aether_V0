import pandas as pd
import pyodbc
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SERVER   = "DESKTOP-Q5KEU1E"
DATABASE = "AetherDW_V0"

print("Starting SQL load pipeline...")

conn = pyodbc.connect(
    f"DRIVER={{SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
)
cursor = conn.cursor()

df = pd.read_csv(os.path.join(ROOT, "data", "processed", "environmental_features.csv"))
print(f"  Rows to load: {len(df)}")


# ── Helper — safely get value or None ─────────────────────────────────────
def val(row, col):
    v = row.get(col)
    if v is None:
        return None
    try:
        import math
        if math.isnan(float(v)):
            return None
    except (TypeError, ValueError):
        pass
    return v


# ── WeatherMetrics ─────────────────────────────────────────────────────────
print("Inserting into WeatherMetrics...")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO WeatherMetrics
            (date, temperature, humidity, wind, pressure,
            cloud_cover, sunshine_duration, heat_index, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    val(row, "date"),
    val(row, "temperature"),
    val(row, "humidity"),
    val(row, "wind"),
    val(row, "pressure"),
    val(row, "cloud_cover"),
    val(row, "sunshine_duration"),
    val(row, "heat_index"),
    "historical"
    )
conn.commit()
print(f"  WeatherMetrics: {len(df)} rows inserted.")


# ── PollutionMetrics ───────────────────────────────────────────────────────
print("Inserting into PollutionMetrics...")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO PollutionMetrics
            (date, pm25, pm10, aqi, european_aqi,
            ozone, nitrogen_dioxide, sulphur_dioxide,
            dust, uv_index, pollution_level, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    val(row, "date"),
    val(row, "pm25"),
    val(row, "pm10"),
    val(row, "aqi"),
    val(row, "european_aqi"),
    val(row, "ozone"),
    val(row, "nitrogen_dioxide"),
    val(row, "sulphur_dioxide"),
    val(row, "dust"),
    val(row, "uv_index"),
    val(row, "pollution_level"),
    "historical"
    )
conn.commit()
print(f"  PollutionMetrics: {len(df)} rows inserted.")


# ── EnvironmentalFeatures ──────────────────────────────────────────────────
print("Inserting into EnvironmentalFeatures...")
for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO EnvironmentalFeatures
            (date, temperature, humidity, wind, pressure,
            cloud_cover, sunshine_duration,
            pm25, pm10, aqi, european_aqi,
            ozone, nitrogen_dioxide, sulphur_dioxide,
            dust, uv_index,
            heat_index, pollution_level,
            respiratory_stress, uv_risk,
            health_category, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    val(row, "date"),
    val(row, "temperature"),
    val(row, "humidity"),
    val(row, "wind"),
    val(row, "pressure"),
    val(row, "cloud_cover"),
    val(row, "sunshine_duration"),
    val(row, "pm25"),
    val(row, "pm10"),
    val(row, "aqi"),
    val(row, "european_aqi"),
    val(row, "ozone"),
    val(row, "nitrogen_dioxide"),
    val(row, "sulphur_dioxide"),
    val(row, "dust"),
    val(row, "uv_index"),
    val(row, "heat_index"),
    val(row, "pollution_level"),
    val(row, "respiratory_stress"),
    val(row, "uv_risk"),
    val(row, "health_category"),
    "historical"
    )
conn.commit()
print(f"  EnvironmentalFeatures: {len(df)} rows inserted.")


# ── DimDate ────────────────────────────────────────────────────────────────
print("Populating DimDate...")
dates = pd.to_datetime(df["date"], errors="coerce").dropna().unique()
inserted = 0
for d in dates:
    try:
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM DimDate WHERE date = ?)
            INSERT INTO DimDate
                (date, year, month, month_name, quarter,
                week, day_of_week, is_weekend)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        d.date(),
        d.date(),
        d.year,
        d.month,
        d.strftime("%B"),
        (d.month - 1) // 3 + 1,
        d.isocalendar()[1],
        d.strftime("%A"),
        1 if d.weekday() >= 5 else 0
        )
        inserted += 1
    except Exception:
        pass
conn.commit()
print(f"  DimDate: {inserted} dates inserted.")


cursor.close()
conn.close()
print("\nSQL loading completed.")



# The `val()` helper function is important — it converts pandas `NaN` values to Python `None` before inserting, 
# which is what SQL Server expects for nullable columns. 
# Without it you would get data type errors on every row that has empty pollution fields.

# Run it with:
# python pipelines/loading/load_to_sql.py