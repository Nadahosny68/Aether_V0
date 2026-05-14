import pyodbc
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import urllib

load_dotenv()

# ── Azure connection ──────────────────────────────────────────────────────────
AZURE_CONN_STR = (
    f"Driver={{{os.getenv('AZURE_SQL_DRIVER')}}};"
    f"Server=tcp:{os.getenv('AZURE_SQL_SERVER')},1433;"
    f"Database={os.getenv('AZURE_SQL_DATABASE')};"
    f"Uid={os.getenv('AZURE_SQL_USER')};"
    f"Pwd={os.getenv('AZURE_SQL_PASSWORD')};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

# ── Local connection ──────────────────────────────────────────────────────────
LOCAL_CONN_STR = (
    f"Driver={{{os.getenv('SQL_DRIVER')}}};"
    f"Server={os.getenv('SQL_SERVER')};"
    f"Database={os.getenv('SQL_DATABASE')};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

def get_azure_engine():
    params = urllib.parse.quote_plus(AZURE_CONN_STR)
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}",
        fast_executemany=True
    )

def get_local_engine():
    params = urllib.parse.quote_plus(LOCAL_CONN_STR)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def get_azure_conn():
    return pyodbc.connect(AZURE_CONN_STR)

# ── Step 1: Create schemas on Azure ──────────────────────────────────────────
def create_azure_schemas():
    print("\n── Creating schemas on Azure ────────────")
    conn = get_azure_conn()
    cursor = conn.cursor()
    for schema in ["Bronze", "Silver", "Gold"]:
        try:
            cursor.execute(f"""
                IF NOT EXISTS (
                    SELECT * FROM sys.schemas WHERE name = '{schema}'
                )
                EXEC('CREATE SCHEMA [{schema}]')
            """)
            print(f"   ✅ Schema '{schema}' ready")
        except Exception as e:
            print(f"   ❌ Schema '{schema}' failed: {e}")
    conn.commit()
    conn.close()

# ── Step 2: Create tables on Azure ───────────────────────────────────────────
def create_azure_tables():
    print("\n── Creating tables on Azure ─────────────")
    conn = get_azure_conn()
    cursor = conn.cursor()

    tables = {
        "Gold.DimDate": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects WHERE name='DimDate' AND xtype='U'
            )
            CREATE TABLE Gold.DimDate (
                date        DATE PRIMARY KEY,
                year        INT, month INT, month_name VARCHAR(20),
                quarter     INT, week  INT, day_of_week VARCHAR(20),
                is_weekend  BIT
            )
        """,
        "Gold.EnvironmentalFeatures": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects
                WHERE name='EnvironmentalFeatures' AND xtype='U'
            )
            CREATE TABLE Gold.EnvironmentalFeatures (
                id                    INT IDENTITY(1,1) PRIMARY KEY,
                date                  DATE NOT NULL,
                temperature           FLOAT, humidity    FLOAT,
                wind                  FLOAT, pressure    FLOAT,
                precipitation         FLOAT, uv_index    FLOAT,
                sunshine_duration     FLOAT, pm25        FLOAT,
                pm10                  FLOAT, aqi         FLOAT,
                ozone                 FLOAT, nitrogen_dioxide  FLOAT,
                sulphur_dioxide       FLOAT, carbon_monoxide   FLOAT,
                aerosol_optical_depth FLOAT, heat_index        FLOAT,
                pollution_level       FLOAT, respiratory_stress FLOAT,
                uv_risk               VARCHAR(50), dust_risk_index FLOAT,
                rain_wash_effect      FLOAT, heat_stress_peak   FLOAT,
                temperature_range     FLOAT, health_category    VARCHAR(100),
                source                VARCHAR(50)
            )
        """,
        "Gold.RiskPredictions": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects
                WHERE name='RiskPredictions' AND xtype='U'
            )
            CREATE TABLE Gold.RiskPredictions (
                id              INT IDENTITY(1,1) PRIMARY KEY,
                date            DATE NOT NULL,
                health_category VARCHAR(100),
                aqi             FLOAT, pm25 FLOAT,
                model_version   VARCHAR(50),
                predicted_at    DATETIME DEFAULT GETDATE()
            )
        """,
        "Gold.ForecastPredictions": """
            IF NOT EXISTS (
                SELECT * FROM sysobjects
                WHERE name='ForecastPredictions' AND xtype='U'
            )
            CREATE TABLE Gold.ForecastPredictions (
                id                 INT IDENTITY(1,1) PRIMARY KEY,
                forecast_date      DATE NOT NULL,
                forecast_horizon   INT,
                predicted_category VARCHAR(100),
                confidence         FLOAT,
                generated_at       DATETIME DEFAULT GETDATE(),
                model_version      VARCHAR(50)
            )
        """
    }

    for name, sql in tables.items():
        try:
            cursor.execute(sql)
            print(f"   ✅ Table '{name}' ready")
        except Exception as e:
            print(f"   ❌ Table '{name}' failed: {e}")

    conn.commit()
    conn.close()

# ── Step 3: Copy all data from local to Azure ─────────────────────────────────
def migrate_table(table_name, schema="Gold"):
    print(f"\n── Migrating {schema}.{table_name} ──────────")
    try:
        local_engine = get_local_engine()
        azure_engine = get_azure_engine()

        # Read from local
        df = pd.read_sql(
            f"SELECT * FROM {schema}.{table_name}", local_engine
        )

        # Drop identity column (Azure recreates it)
        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        print(f"   📦 {len(df)} rows read from local")

        # Clear Azure table first
        with azure_engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {schema}.{table_name}"))
            conn.commit()

        # Write to Azure in chunks
        df.to_sql(
            name=table_name,
            schema=schema,
            con=azure_engine,
            if_exists="append",
            index=False,
            chunksize=500
        )
        print(f"   ✅ {len(df)} rows migrated to Azure")

    except Exception as e:
        print(f"   ❌ Migration failed: {e}")

# ── Step 4: Verify row counts match ──────────────────────────────────────────
def verify_migration():
    print("\n── Verifying migration ──────────────────")
    local_engine = get_local_engine()
    azure_engine = get_azure_engine()

    tables = [
        "Gold.EnvironmentalFeatures",
        "Gold.RiskPredictions",
        "Gold.ForecastPredictions",
        "Gold.DimDate"
    ]

    print(f"   {'Table':<35} {'Local':>8} {'Azure':>8} {'Match':>6}")
    print(f"   {'-'*60}")

    for t in tables:
        try:
            local_cnt = pd.read_sql(
                f"SELECT COUNT(*) as cnt FROM {t}", local_engine
            )['cnt'].values[0]
            azure_cnt = pd.read_sql(
                f"SELECT COUNT(*) as cnt FROM {t}", azure_engine
            )['cnt'].values[0]
            match = "✅" if local_cnt == azure_cnt else "❌"
            print(f"   {t:<35} {local_cnt:>8} {azure_cnt:>8} {match:>6}")
        except Exception as e:
            print(f"   {t}: ❌ {e}")

# ── Run everything ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Starting Azure Migration...")

    create_azure_schemas()
    create_azure_tables()

    migrate_table("EnvironmentalFeatures")
    migrate_table("RiskPredictions")
    migrate_table("ForecastPredictions")
    migrate_table("DimDate")

    verify_migration()

    print("\n✅ Migration complete!")