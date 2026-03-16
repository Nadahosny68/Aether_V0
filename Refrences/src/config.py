import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration for the Visual Crossing API
class Config:
    VISUALCROSSING_API_KEY = os.getenv("VISUALCROSSING_API_KEY")
    AIRVISUAL_API_KEY = os.getenv("AIRVISUAL_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Example default values; adjust or extend as needed
    DEFAULT_CITY = "ioannina"
    DEFAULT_STATE = "epirus"
    DEFAULT_COUNTRY = "greece"
    DEFAULT_START_DATE = "2024-06-03"
    DEFAULT_END_DATE = "2024-09-03"
