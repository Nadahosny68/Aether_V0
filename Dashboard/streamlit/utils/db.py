import os
import urllib
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_engine():

    conn_str = (
        f"Driver={{{os.getenv('SQL_DRIVER')}}};"
        f"Server=tcp:{os.getenv('SQL_SERVER')},1433;"
        f"Database={os.getenv('SQL_DATABASE')};"
        f"Uid={os.getenv('SQL_USERNAME')};"
        f"Pwd={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    params = urllib.parse.quote_plus(conn_str)

    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}",
        pool_pre_ping=True
    )