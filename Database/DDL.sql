CREATE TABLE WeatherMetrics (
    id INT IDENTITY(1,1) PRIMARY KEY,
    date DATE,
    temperature FLOAT,
    humidity FLOAT,
    wind FLOAT,
    heat_index FLOAT
);

CREATE TABLE PollutionMetrics (
    id INT IDENTITY(1,1) PRIMARY KEY,
    date DATE,
    pm25 FLOAT,
    pm10 FLOAT,
    aqi FLOAT,
    pollution_level FLOAT
);

SELECT * FROM WeatherMetrics;
SELECT * FROM PollutionMetrics;


SELECT TOP 10 * FROM WeatherMetrics;
SELECT TOP 10 * FROM PollutionMetrics;


TRUNCATE TABLE WeatherMetrics;
TRUNCATE TABLE PollutionMetrics;

CREATE TABLE RiskPredictions (
    id INT IDENTITY(1,1) PRIMARY KEY,
    date DATE,
    temperature FLOAT,
    humidity FLOAT,
    wind FLOAT,
    heat_index FLOAT,
    pm25 FLOAT,
    pm10 FLOAT,
    aqi FLOAT,
    pollution_level FLOAT,
    predicted_risk VARCHAR(20)
);


SELECT TOP 200 * FROM RiskPredictions;

SELECT  * FROM RiskPredictions
where predicted_risk = 'low';


-- Add new columns to WeatherMetrics
ALTER TABLE WeatherMetrics
ADD pressure FLOAT, uv_index FLOAT, cloud_cover FLOAT;

-- Add new columns to PollutionMetrics  
ALTER TABLE PollutionMetrics
ADD ozone FLOAT, nitrogen_dioxide FLOAT, sulphur_dioxide FLOAT, dust FLOAT, european_aqi FLOAT;

-- Add health_category to RiskPredictions (replaces the binary predicted_risk)
ALTER TABLE RiskPredictions
ADD health_category VARCHAR(40);