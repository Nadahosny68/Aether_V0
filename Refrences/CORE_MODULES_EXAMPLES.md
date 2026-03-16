# Aether Platform - Core Python Module Examples
## Detailed Code Structure for Production-Ready Data Engineering

This document provides complete, production-ready code examples for the core modules of the Aether platform.

---

## 📁 Directory: `src/data_collection/`

### File: `weather_api.py`

```python
"""
Weather data collection module.

Fetches weather data from OpenWeatherMap API for Cairo, Egypt.
Implements retry logic, rate limiting, and error handling.
"""

import os
import time
from typing import Dict, Optional, List
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger


class WeatherAPIClient:
    """Client for fetching weather data from OpenWeatherMap."""
    
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather API client.
        
        Args:
            api_key: OpenWeatherMap API key (reads from env if not provided)
        """
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not provided. Set OPENWEATHER_API_KEY env variable.")
        
        self.session = self._create_session()
        logger.info("WeatherAPIClient initialized successfully")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def fetch_current_weather(
        self,
        city: str = "Cairo",
        country_code: str = "EG"
    ) -> Dict:
        """
        Fetch current weather data for a city.
        
        Args:
            city: City name
            country_code: ISO 3166 country code
        
        Returns:
            Dictionary containing weather data
        
        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.BASE_URL}/weather"
        params = {
            "q": f"{city},{country_code}",
            "appid": self.api_key,
            "units": "metric"
        }
        
        try:
            logger.info(f"Fetching weather data for {city}, {country_code}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.success(f"Successfully fetched weather data for {city}")
            
            return self._parse_weather_response(data)
        
        except requests.RequestException as e:
            logger.error(f"Failed to fetch weather data: {str(e)}")
            raise
    
    def fetch_forecast(
        self,
        city: str = "Cairo",
        country_code: str = "EG",
        days: int = 5
    ) -> List[Dict]:
        """
        Fetch weather forecast for upcoming days.
        
        Args:
            city: City name
            country_code: ISO 3166 country code
            days: Number of days to forecast (max 5)
        
        Returns:
            List of dictionaries containing forecast data
        """
        url = f"{self.BASE_URL}/forecast"
        params = {
            "q": f"{city},{country_code}",
            "appid": self.api_key,
            "units": "metric",
            "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
        }
        
        try:
            logger.info(f"Fetching {days}-day forecast for {city}")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            forecasts = [
                self._parse_forecast_item(item) 
                for item in data.get("list", [])
            ]
            
            logger.success(f"Successfully fetched forecast for {city}")
            return forecasts
        
        except requests.RequestException as e:
            logger.error(f"Failed to fetch forecast: {str(e)}")
            raise
    
    def _parse_weather_response(self, data: Dict) -> Dict:
        """Parse API response into standardized format."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "city": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "temperature": data.get("main", {}).get("temp"),
            "feels_like": data.get("main", {}).get("feels_like"),
            "humidity": data.get("main", {}).get("humidity"),
            "pressure": data.get("main", {}).get("pressure"),
            "wind_speed": data.get("wind", {}).get("speed"),
            "wind_direction": data.get("wind", {}).get("deg"),
            "cloudiness": data.get("clouds", {}).get("all"),
            "weather_main": data.get("weather", [{}])[0].get("main"),
            "weather_description": data.get("weather", [{}])[0].get("description"),
            "visibility": data.get("visibility"),
            "sunrise": data.get("sys", {}).get("sunrise"),
            "sunset": data.get("sys", {}).get("sunset"),
        }
    
    def _parse_forecast_item(self, item: Dict) -> Dict:
        """Parse forecast item from API response."""
        return {
            "timestamp": item.get("dt_txt"),
            "temperature": item.get("main", {}).get("temp"),
            "humidity": item.get("main", {}).get("humidity"),
            "pressure": item.get("main", {}).get("pressure"),
            "wind_speed": item.get("wind", {}).get("speed"),
            "cloudiness": item.get("clouds", {}).get("all"),
            "weather_main": item.get("weather", [{}])[0].get("main"),
            "pop": item.get("pop", 0) * 100,  # Probability of precipitation
        }
    
    def health_check(self) -> bool:
        """
        Check if API is accessible.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            self.fetch_current_weather()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


# Example usage
if __name__ == "__main__":
    client = WeatherAPIClient()
    
    # Fetch current weather
    current = client.fetch_current_weather("Cairo", "EG")
    print(f"Current temperature in Cairo: {current['temperature']}°C")
    
    # Fetch forecast
    forecast = client.fetch_forecast("Cairo", "EG", days=3)
    print(f"Fetched {len(forecast)} forecast points")
```

---

## 📁 Directory: `src/data_processing/`

### File: `feature_engineer.py`

```python
"""
Feature engineering module for environmental data.

Calculates derived features like Heat Index and Pollution Level.
"""

import numpy as np
import pandas as pd
from typing import Optional
from loguru import logger


class FeatureEngineer:
    """Feature engineering for environmental monitoring data."""
    
    # WHO Air Quality Guidelines (µg/m³)
    WHO_PM25_THRESHOLD = 15
    WHO_PM10_THRESHOLD = 45
    
    # AQI breakpoints
    AQI_BREAKPOINTS = {
        "Good": (0, 50),
        "Moderate": (51, 100),
        "Unhealthy_Sensitive": (101, 150),
        "Unhealthy": (151, 200),
        "Very_Unhealthy": (201, 300),
        "Hazardous": (301, 500)
    }
    
    @staticmethod
    def calculate_heat_index(
        temperature: float,
        humidity: float,
        unit: str = "celsius"
    ) -> float:
        """
        Calculate heat index (feels-like temperature).
        
        Uses Rothfusz regression equation used by NOAA.
        
        Args:
            temperature: Temperature in Celsius or Fahrenheit
            humidity: Relative humidity (0-100%)
            unit: Temperature unit ('celsius' or 'fahrenheit')
        
        Returns:
            Heat index in same unit as input temperature
        
        Raises:
            ValueError: If inputs are invalid
        """
        if not (0 <= humidity <= 100):
            raise ValueError("Humidity must be between 0 and 100")
        
        # Convert to Fahrenheit for calculation
        if unit.lower() == "celsius":
            temp_f = (temperature * 9/5) + 32
        elif unit.lower() == "fahrenheit":
            temp_f = temperature
        else:
            raise ValueError("Unit must be 'celsius' or 'fahrenheit'")
        
        # Simple formula for low temperatures
        if temp_f < 80:
            heat_index_f = temp_f
        else:
            # Rothfusz regression
            c1 = -42.379
            c2 = 2.04901523
            c3 = 10.14333127
            c4 = -0.22475541
            c5 = -0.00683783
            c6 = -0.05481717
            c7 = 0.00122874
            c8 = 0.00085282
            c9 = -0.00000199
            
            T = temp_f
            R = humidity
            
            heat_index_f = (
                c1 + c2*T + c3*R + c4*T*R + c5*T**2 + c6*R**2 + 
                c7*T**2*R + c8*T*R**2 + c9*T**2*R**2
            )
            
            # Adjustments
            if R < 13 and 80 <= T <= 112:
                adjustment = ((13 - R) / 4) * np.sqrt((17 - abs(T - 95)) / 17)
                heat_index_f -= adjustment
            elif R > 85 and 80 <= T <= 87:
                adjustment = ((R - 85) / 10) * ((87 - T) / 5)
                heat_index_f += adjustment
        
        # Convert back to original unit
        if unit.lower() == "celsius":
            return round((heat_index_f - 32) * 5/9, 2)
        else:
            return round(heat_index_f, 2)
    
    @staticmethod
    def calculate_pollution_level(
        pm25: Optional[float],
        pm10: Optional[float],
        aqi: Optional[int]
    ) -> str:
        """
        Calculate pollution level category.
        
        Args:
            pm25: PM2.5 concentration (µg/m³)
            pm10: PM10 concentration (µg/m³)
            aqi: Air Quality Index (0-500)
        
        Returns:
            Pollution level: 'Low', 'Moderate', 'High', 'Very High'
        """
        scores = []
        
        # PM2.5 scoring
        if pm25 is not None and pm25 >= 0:
            if pm25 <= 12:
                scores.append(1)  # Low
            elif pm25 <= 35.4:
                scores.append(2)  # Moderate
            elif pm25 <= 55.4:
                scores.append(3)  # High
            else:
                scores.append(4)  # Very High
        
        # PM10 scoring
        if pm10 is not None and pm10 >= 0:
            if pm10 <= 54:
                scores.append(1)
            elif pm10 <= 154:
                scores.append(2)
            elif pm10 <= 254:
                scores.append(3)
            else:
                scores.append(4)
        
        # AQI scoring
        if aqi is not None and aqi >= 0:
            if aqi <= 50:
                scores.append(1)
            elif aqi <= 100:
                scores.append(2)
            elif aqi <= 150:
                scores.append(3)
            else:
                scores.append(4)
        
        if not scores:
            return "Unknown"
        
        # Take the worst score
        max_score = max(scores)
        
        level_map = {
            1: "Low",
            2: "Moderate",
            3: "High",
            4: "Very High"
        }
        
        return level_map.get(max_score, "Unknown")
    
    @classmethod
    def engineer_features(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add engineered features to dataframe.
        
        Args:
            df: DataFrame with raw weather and air quality data
        
        Returns:
            DataFrame with additional engineered features
        """
        logger.info("Engineering features from raw data")
        
        df = df.copy()
        
        # Calculate Heat Index
        if 'temperature' in df.columns and 'humidity' in df.columns:
            df['heat_index'] = df.apply(
                lambda row: cls.calculate_heat_index(
                    row['temperature'],
                    row['humidity'],
                    unit='celsius'
                ),
                axis=1
            )
            logger.debug("Heat index calculated")
        
        # Calculate Pollution Level
        if all(col in df.columns for col in ['pm25', 'pm10', 'aqi']):
            df['pollution_level'] = df.apply(
                lambda row: cls.calculate_pollution_level(
                    row['pm25'],
                    row['pm10'],
                    row['aqi']
                ),
                axis=1
            )
            logger.debug("Pollution level calculated")
        
        # Time-based features
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['month'] = df['timestamp'].dt.month
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            logger.debug("Time-based features created")
        
        # Interaction features
        if 'temperature' in df.columns and 'humidity' in df.columns:
            df['temp_humidity_interaction'] = df['temperature'] * df['humidity']
        
        if 'pm25' in df.columns and 'pm10' in df.columns:
            df['pm_ratio'] = df['pm25'] / (df['pm10'] + 1)  # Avoid division by zero
        
        logger.success(f"Feature engineering complete. Added {len(df.columns)} features")
        
        return df
    
    @staticmethod
    def create_lag_features(
        df: pd.DataFrame,
        columns: list,
        lags: list = [1, 3, 7]
    ) -> pd.DataFrame:
        """
        Create lagged features for time series.
        
        Args:
            df: DataFrame sorted by time
            columns: Columns to create lags for
            lags: List of lag periods
        
        Returns:
            DataFrame with lagged features
        """
        df = df.copy()
        
        for col in columns:
            for lag in lags:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)
        
        logger.info(f"Created lag features for {len(columns)} columns")
        return df


# Example usage
if __name__ == "__main__":
    # Sample data
    data = {
        'timestamp': pd.date_range('2024-01-01', periods=10, freq='D'),
        'temperature': [30, 32, 31, 33, 35, 34, 36, 38, 37, 35],
        'humidity': [60, 65, 70, 68, 72, 75, 70, 68, 65, 60],
        'pm25': [25, 30, 45, 60, 55, 50, 70, 80, 75, 65],
        'pm10': [50, 60, 80, 100, 95, 90, 120, 140, 130, 110],
        'aqi': [60, 70, 90, 110, 100, 95, 130, 150, 140, 120]
    }
    
    df = pd.DataFrame(data)
    
    # Engineer features
    engineer = FeatureEngineer()
    df_engineered = engineer.engineer_features(df)
    
    print(df_engineered[['temperature', 'humidity', 'heat_index', 
                         'pollution_level']].head())
```

---

## 📁 Directory: `src/database/`

### File: `connection.py`

```python
"""
Database connection management for SQL Server.

Implements connection pooling, retry logic, and transaction management.
"""

import os
from typing import Optional, Any, List, Dict
from contextlib import contextmanager
import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from loguru import logger


class DatabaseConnection:
    """Manages SQL Server database connections."""
    
    def __init__(
        self,
        server: Optional[str] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        driver: str = "ODBC Driver 17 for SQL Server"
    ):
        """
        Initialize database connection manager.
        
        Args:
            server: SQL Server hostname
            database: Database name
            username: Database username
            password: Database password
            driver: ODBC driver name
        """
        self.server = server or os.getenv("DB_SERVER")
        self.database = database or os.getenv("DB_NAME")
        self.username = username or os.getenv("DB_USER")
        self.password = password or os.getenv("DB_PASSWORD")
        self.driver = driver
        
        self._validate_credentials()
        
        # Create SQLAlchemy engine
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        logger.info(f"Database connection initialized for {self.database}")
    
    def _validate_credentials(self):
        """Validate that all required credentials are provided."""
        required = {
            "server": self.server,
            "database": self.database,
            "username": self.username,
            "password": self.password
        }
        
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing database credentials: {', '.join(missing)}")
    
    def _create_engine(self):
        """Create SQLAlchemy engine with connection pooling."""
        connection_string = (
            f"mssql+pyodbc://{self.username}:{self.password}"
            f"@{self.server}/{self.database}"
            f"?driver={self.driver.replace(' ', '+')}"
        )
        
        engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            echo=False
        )
        
        return engine
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        
        Yields:
            SQLAlchemy session
        
        Example:
            >>> with db.get_session() as session:
            ...     result = session.execute(query)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict] = None,
        fetch: bool = True
    ) -> Optional[List[Dict]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
        
        Returns:
            List of result dictionaries if fetch=True, None otherwise
        """
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            
            if fetch:
                # Convert results to list of dicts
                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                return None
    
    def bulk_insert(
        self,
        table_name: str,
        data: List[Dict],
        batch_size: int = 1000
    ):
        """
        Bulk insert data into table.
        
        Args:
            table_name: Target table name
            data: List of dictionaries to insert
            batch_size: Number of rows per batch
        """
        if not data:
            logger.warning("No data to insert")
            return
        
        columns = list(data[0].keys())
        placeholders = ", ".join([f":{col}" for col in columns])
        column_names = ", ".join(columns)
        
        query = f"""
            INSERT INTO {table_name} ({column_names})
            VALUES ({placeholders})
        """
        
        with self.get_session() as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                session.execute(text(query), batch)
                logger.debug(f"Inserted batch {i//batch_size + 1}")
        
        logger.success(f"Bulk inserted {len(data)} rows into {table_name}")
    
    def test_connection(self) -> bool:
        """
        Test database connectivity.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.success("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
    
    def close(self):
        """Close all database connections."""
        self.engine.dispose()
        logger.info("Database connections closed")


# Example usage
if __name__ == "__main__":
    db = DatabaseConnection()
    
    # Test connection
    if db.test_connection():
        print("Database connected successfully")
    
    # Execute query
    results = db.execute_query("SELECT TOP 10 * FROM weather_data")
    print(f"Fetched {len(results)} rows")
    
    # Bulk insert example
    sample_data = [
        {"city": "Cairo", "temperature": 30.5, "humidity": 65},
        {"city": "Cairo", "temperature": 31.2, "humidity": 68}
    ]
    db.bulk_insert("weather_data", sample_data)
```

Continue in next response for remaining modules...
