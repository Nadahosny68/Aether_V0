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