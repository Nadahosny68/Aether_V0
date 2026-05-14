import pyodbc
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import urllib

# ── Load password from .env ──────────────────────────────────────────────────
load_dotenv()

SQL_SERVER   = os.getenv("SQL_SERVER")    # DESKTOP-Q5KEU1E
SQL_DATABASE = os.getenv("SQL_DATABASE")  # AetherDW_V0
SQL_DRIVER   = os.getenv("SQL_DRIVER")    # ODBC Driver 17 for SQL Server

# ── Connection string ─────────────────────────────────────────────────────────
CONN_STR = (
    f"Driver={{{SQL_DRIVER}}};"
    f"Server={SQL_SERVER};"
    f"Database={SQL_DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

# ── SQLAlchemy engine (used for pandas read/write) ────────────────────────────
def get_engine():
    params = urllib.parse.quote_plus(CONN_STR)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return engine

# ── Raw pyodbc connection (used for schema creation) ─────────────────────────
def get_connection():
    return pyodbc.connect(CONN_STR)

# ── Test connection ───────────────────────────────────────────────────────────
def test_connection():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print("✅ Connected successfully!")
        print(f"   SQL Server version: {row[0][:50]}")
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

# ── Create all schemas ────────────────────────────────────────────────────────
def create_schemas():
    conn = get_connection()
    cursor = conn.cursor()
    schemas = ["Bronze", "Silver", "Gold"]
    for schema in schemas:
        try:
            cursor.execute(f"""
                IF NOT EXISTS (
                    SELECT * FROM sys.schemas WHERE name = '{schema}'
                )
                EXEC('CREATE SCHEMA {schema}')
            """)
            print(f"✅ Schema '{schema}' ready")
        except Exception as e:
            print(f"❌ Schema '{schema}' failed: {e}")
    conn.commit()
    conn.close()

# ── Create all tables ─────────────────────────────────────────────────────────
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    tables = {

        # ── DimDate ──────────────────────────────────────────────────────────
        "Gold.DimDate": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects WHERE name='DimDate' AND xtype='U'
            )
            CREATE TABLE Gold.DimDate (
                date          DATE PRIMARY KEY,
                year          INT,
                month         INT,
                month_name    VARCHAR(20),
                quarter       INT,
                week          INT,
                day_of_week   VARCHAR(20),
                is_weekend    BIT
            )
        """,

        # ── EnvironmentalFeatures ─────────────────────────────────────────────
        "Gold.EnvironmentalFeatures": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects WHERE name='EnvironmentalFeatures' AND xtype='U'
            )
            CREATE TABLE Gold.EnvironmentalFeatures (
                id                    INT IDENTITY(1,1) PRIMARY KEY,
                date                  DATE NOT NULL,
                temperature           FLOAT,
                humidity              FLOAT,
                wind                  FLOAT,
                pressure              FLOAT,
                precipitation         FLOAT,
                uv_index              FLOAT,
                sunshine_duration     FLOAT,
                pm25                  FLOAT,
                pm10                  FLOAT,
                aqi                   FLOAT,
                ozone                 FLOAT,
                nitrogen_dioxide      FLOAT,
                sulphur_dioxide       FLOAT,
                carbon_monoxide       FLOAT,
                aerosol_optical_depth FLOAT,
                heat_index            FLOAT,
                pollution_level       FLOAT,
                respiratory_stress    FLOAT,
                uv_risk               VARCHAR(50),
                dust_risk_index       FLOAT,
                rain_wash_effect      FLOAT,
                heat_stress_peak      FLOAT,
                temperature_range     FLOAT,
                health_category       VARCHAR(100),
                source                VARCHAR(50)
            )
        """,

        # ── RiskPredictions ───────────────────────────────────────────────────
        "Gold.RiskPredictions": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects WHERE name='RiskPredictions' AND xtype='U'
            )
            CREATE TABLE Gold.RiskPredictions (
                id              INT IDENTITY(1,1) PRIMARY KEY,
                date            DATE NOT NULL,
                health_category VARCHAR(100),
                aqi             FLOAT,
                pm25            FLOAT,
                model_version   VARCHAR(50),
                predicted_at    DATETIME DEFAULT GETDATE()
            )
        """,

        # ── ForecastPredictions ───────────────────────────────────────────────
        "Gold.ForecastPredictions": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects WHERE name='ForecastPredictions' AND xtype='U'
            )
            CREATE TABLE Gold.ForecastPredictions (
                id                  INT IDENTITY(1,1) PRIMARY KEY,
                forecast_date       DATE NOT NULL,
                forecast_horizon    INT,
                predicted_category  VARCHAR(100),
                confidence          FLOAT,
                generated_at        DATETIME DEFAULT GETDATE(),
                model_version       VARCHAR(50)
            )
        """
    }

    for table_name, sql in tables.items():
        try:
            cursor.execute(sql)
            print(f"✅ Table '{table_name}' ready")
        except Exception as e:
            print(f"❌ Table '{table_name}' failed: {e}")

    conn.commit()
    conn.close()

# ── Load CSV into EnvironmentalFeatures ───────────────────────────────────────
def load_environmental_csv(csv_path: str):
    """
    Pass the path to your environmental_features.csv
    This will bulk-load it into Gold.EnvironmentalFeatures
    """
    try:
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date']).dt.date

        # Keep only historical rows, not live API rows
        if 'source' in df.columns:
            df_hist = df[df['source'] != 'api_daily']
        else:
            df_hist = df

        engine = get_engine()

        # Delete existing historical rows first (refresh strategy)
        with engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM Gold.EnvironmentalFeatures
                WHERE source != 'api_daily' OR source IS NULL
            """))
            conn.commit()

        # Load fresh
        df_hist.to_sql(
            name="EnvironmentalFeatures",
            schema="Gold",
            con=engine,
            if_exists="append",
            index=False
        )
        print(f"✅ Loaded {len(df_hist)} historical rows into EnvironmentalFeatures")

    except Exception as e:
        print(f"❌ CSV load failed: {e}")

# ── Populate DimDate from EnvironmentalFeatures ───────────────────────────────
def populate_dimdate():
    try:
        engine = get_engine()
        df = pd.read_sql(
            "SELECT DISTINCT date FROM Gold.EnvironmentalFeatures", engine
        )
        df['date'] = pd.to_datetime(df['date'])
        df['year']        = df['date'].dt.year
        df['month']       = df['date'].dt.month
        df['month_name']  = df['date'].dt.strftime('%B')
        df['quarter']     = df['date'].dt.quarter
        df['week']        = df['date'].dt.isocalendar().week.astype(int)
        df['day_of_week'] = df['date'].dt.strftime('%A')
        df['is_weekend']  = df['date'].dt.weekday >= 5
        df['date']        = df['date'].dt.date

        df.to_sql(
            name="DimDate",
            schema="Gold",
            con=engine,
            if_exists="replace",
            index=False
        )
        print(f"✅ DimDate populated with {len(df)} dates")

    except Exception as e:
        print(f"❌ DimDate population failed: {e}")

# ── Quick data check ──────────────────────────────────────────────────────────
def check_data():
    engine = get_engine()
    tables = [
        "Gold.EnvironmentalFeatures",
        "Gold.RiskPredictions",
        "Gold.ForecastPredictions",
        "Gold.DimDate"
    ]
    print("\n── Row counts ───────────────────────────")
    for t in tables:
        try:
            df = pd.read_sql(f"SELECT COUNT(*) as cnt FROM {t}", engine)
            print(f"   {t}: {df['cnt'].values[0]} rows")
        except Exception as e:
            print(f"   {t}: ❌ {e}")

# ── Main: run all setup steps ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n── Step 1: Test connection ──────────────")
    test_connection()

    print("\n── Step 2: Create schemas ───────────────")
    create_schemas()

    print("\n── Step 3: Create tables ────────────────")
    create_tables()

    # ── Uncomment this after you confirm connection works ──
    # print("\n── Step 4: Load CSV ─────────────────────")
    # load_environmental_csv("data/environmental_features.csv")

    # print("\n── Step 5: Populate DimDate ─────────────")
    # populate_dimdate()

    print("\n── Step 6: Check row counts ─────────────")
    check_data()