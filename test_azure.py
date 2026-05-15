# save as test_azure.py in your project root and run it
import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

conn_str = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:aether-server.database.windows.net,1433;"
    f"Database=AetherDB;"
    f"Uid=aether-server;"
    f"Pwd=NadaHosny@2026;"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=60;"
)

try:
    conn = pyodbc.connect(conn_str)
    print("✅ Azure connected!")
    conn.close()
except Exception as e:
    print(f"❌ Failed: {e}")