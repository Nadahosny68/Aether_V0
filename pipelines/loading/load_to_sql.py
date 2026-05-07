"""
pipelines/loading/load_to_sql.py
─────────────────────────────────
Replaces the SSIS package entirely.
Loads data/processed/environmental_features.csv directly into
EnvironmentalFeatures table using pyodbc — no SSIS license needed.

Behaviour:
- TRUNCATEs EnvironmentalFeatures first (same as SSIS package did)
- Bulk inserts all rows from the CSV
- Populates DimDate from the new data
- Fast: uses executemany for batch insert

Usage:
    python pipelines/loading/load_to_sql.py
"""

import os
import sys
import pyodbc
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

from utils.logger import get_logger
log = get_logger("load_to_sql")

CSV_PATH = os.path.join(ROOT, "data", "processed", "environmental_features.csv")

# All columns that exist in the EnvironmentalFeatures SQL table
# Must match your DDL exactly — columns not in CSV are skipped safely
SQL_COLUMNS = [
    "date", "temperature", "humidity", "wind", "pressure",
    "cloud_cover", "sunshine_duration",
    "temp_max", "temp_min", "apparent_temp_max", "apparent_temp_min", "apparent_temp_mean",
    "humidity_max", "humidity_min", "wind_max", "wind_gust_max",
    "precipitation", "rain_sum", "dew_point", "shortwave_radiation", "vapour_pressure_deficit",
    "pm25", "pm10", "aqi", "european_aqi",
    "ozone", "nitrogen_dioxide", "sulphur_dioxide",
    "dust", "uv_index", "carbon_monoxide", "aerosol_optical_depth",
    "heat_index", "pollution_level", "respiratory_stress", "uv_risk",
    "temp_range", "heat_stress_peak", "dust_risk_index", "rain_wash_effect",
    "health_category",
]


def get_connection() -> pyodbc.Connection:
    server   = os.environ.get("SQL_SERVER",   "DESKTOP-Q5KEU1E")
    database = os.environ.get("SQL_DATABASE", "AetherDW_V0")
    driver   = os.environ.get("SQL_DRIVER",   "ODBC Driver 17 for SQL Server")
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str, autocommit=False)


def load_csv() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"CSV not found: {CSV_PATH}\n"
            "Run feature_engineering.py first."
        )
    df = pd.read_csv(CSV_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    log.info("Loaded CSV: %d rows, %d columns", len(df), len(df.columns))
    return df


def truncate_and_insert(df: pd.DataFrame, conn: pyodbc.Connection) -> int:
    cursor = conn.cursor()

    # NEW — only deletes rows loaded from CSV, preserves live api_daily rows
    log.info("deletes rows loaded from CSV in EnvironmentalFeatures …")
    cursor.execute("DELETE FROM Gold.EnvironmentalFeatures WHERE source IS NULL OR source != 'api_daily'")

    # Determine which SQL columns are actually in the CSV
    available = [c for c in SQL_COLUMNS if c in df.columns]
    missing   = [c for c in SQL_COLUMNS if c not in df.columns]
    if missing:
        log.warning("Columns in SQL table but not in CSV (will be NULL): %s", missing)

    # Build INSERT statement
    placeholders = ", ".join(["?"] * len(available))
    col_list     = ", ".join(available)
    insert_sql   = f"INSERT INTO Gold.EnvironmentalFeatures ({col_list}) VALUES ({placeholders})"

    # Prepare rows — replace NaN with None so pyodbc writes NULL
    rows = []
    for _, row in df.iterrows():
        values = []
        for col in available:
            val = row[col]
            # Convert numpy/pandas types to Python natives
            if pd.isna(val):
                values.append(None)
            elif hasattr(val, "item"):
                values.append(val.item())
            else:
                values.append(val)
        rows.append(tuple(values))

    # Batch insert in chunks of 500 for performance
    chunk_size = 500
    inserted   = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        cursor.executemany(insert_sql, chunk)
        inserted += len(chunk)
        log.info("  Inserted %d / %d rows …", inserted, len(rows))

    conn.commit()
    log.info("EnvironmentalFeatures loaded: %d rows", inserted)
    return inserted


def populate_dimdate(conn: pyodbc.Connection) -> None:
    """Populates DimDate from EnvironmentalFeatures — same logic as before."""
    log.info("Populating DimDate …")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Gold.DimDate (date, year, month, month_name, quarter, week, day_of_week, is_weekend)
        SELECT DISTINCT
            CAST(ef.date AS DATE),
            YEAR(ef.date),
            MONTH(ef.date),
            DATENAME(MONTH, ef.date),
            DATEPART(QUARTER, ef.date),
            DATEPART(WEEK, ef.date),
            DATENAME(WEEKDAY, ef.date),
            CASE WHEN DATEPART(WEEKDAY, ef.date) IN (1,7) THEN 1 ELSE 0 END
        FROM Gold.EnvironmentalFeatures ef
        WHERE ef.date IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM Gold.DimDate d WHERE d.date = CAST(ef.date AS DATE)
        )
    """)
    conn.commit()
    log.info("DimDate populated")


def run():
    log.info("Starting SQL load (replaces SSIS) …")

    df   = load_csv()
    conn = get_connection()

    try:
        inserted = truncate_and_insert(df, conn)
        populate_dimdate(conn)
        log.info("Load completed successfully: %d rows inserted", inserted)
    except Exception as e:
        conn.rollback()
        log.error("Load failed — rolled back: %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()