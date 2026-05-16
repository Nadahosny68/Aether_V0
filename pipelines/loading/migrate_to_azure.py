import pyodbc
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import urllib

load_dotenv()

# ── Connections ───────────────────────────────────────────────────────────────
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

# ── Step 1: Create schemas ────────────────────────────────────────────────────
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

# ── Step 2: Migrate table — auto schema from local ────────────────────────────
def migrate_table(table_name, schema="Gold"):
    print(f"\n── Migrating {schema}.{table_name} ──────────")
    try:
        local_engine = get_local_engine()
        azure_engine = get_azure_engine()

        # Read ALL columns exactly as they exist locally
        df = pd.read_sql(f"SELECT * FROM {schema}.{table_name}", local_engine)
        print(f"   📦 {len(df)} rows, {len(df.columns)} columns read from local")
        print(f"   📋 Columns: {list(df.columns)}")

        # Drop identity/auto-increment columns
        for drop_col in ['id', 'date_id']:
            if drop_col in df.columns:
                df = df.drop(columns=[drop_col])
                print(f"   🗑️  Dropped identity column '{drop_col}'")

        # Drop existing Azure table and recreate from local schema
        with azure_engine.connect() as conn:
            conn.execute(text(
                f"IF OBJECT_ID('{schema}.{table_name}', 'U') IS NOT NULL "
                f"DROP TABLE {schema}.{table_name}"
            ))
            conn.commit()
        print(f"   🗑️  Dropped old Azure table")

        # Write to Azure — pandas creates table with correct schema automatically
        df.to_sql(
            name=table_name,
            schema=schema,
            con=azure_engine,
            if_exists="replace",   # creates table matching local schema
            index=False,
            chunksize=500
        )
        print(f"   ✅ {len(df)} rows migrated to Azure")

    except Exception as e:
        print(f"   ❌ Migration failed: {e}")

# ── Step 3: Verify ────────────────────────────────────────────────────────────
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

# ── Step 4: Show Azure columns (for debugging) ────────────────────────────────
def show_azure_columns():
    print("\n── Azure column verification ────────────")
    azure_engine = get_azure_engine()
    tables = [
        "EnvironmentalFeatures",
        "RiskPredictions",
        "ForecastPredictions",
        "DimDate"
    ]
    for t in tables:
        try:
            df = pd.read_sql(
                f"SELECT TOP 0 * FROM Gold.{t}", azure_engine
            )
            print(f"   {t}: {len(df.columns)} columns → {list(df.columns)}")
        except Exception as e:
            print(f"   {t}: ❌ {e}")

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Starting Azure Migration...")

    create_azure_schemas()

    migrate_table("EnvironmentalFeatures")
    migrate_table("RiskPredictions")
    migrate_table("ForecastPredictions")
    migrate_table("DimDate")

    verify_migration()
    show_azure_columns()

    print("\n✅ Migration complete!")