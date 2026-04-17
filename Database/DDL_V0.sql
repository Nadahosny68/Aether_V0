-- ============================================================
-- Aether Data Warehouse_02.sql
-- Environmental Health Intelligence Platform
-- ============================================================

CREATE DATABASE AetherDW_V0;
GO

USE AetherDW_V0;
GO

-- ── Dimension: Date ───────────────────────────────────────────────────────
-- Central time dimension for all fact tables
CREATE TABLE DimDate (
    date_id     INT IDENTITY(1,1) PRIMARY KEY,
    date        DATE NOT NULL UNIQUE,
    year        INT,
    month       INT,
    month_name  VARCHAR(20),
    quarter     INT,
    week        INT,
    day_of_week VARCHAR(20),
    is_weekend  BIT
);

-- ── Fact: Weather Metrics ─────────────────────────────────────────────────
CREATE TABLE WeatherMetrics (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    date                DATE NOT NULL,
    temperature         FLOAT,          -- degrees Celsius (mean daily)
    temp_max                FLOAT,
    temp_min                FLOAT,
    apparent_temp_max       FLOAT,
    apparent_temp_min       FLOAT,
    apparent_temp_mean      FLOAT,
    humidity                FLOAT,          -- relative humidity %
    humidity_max            FLOAT,
    humidity_min            FLOAT,
    wind                    FLOAT,          -- wind speed m/s
    wind_max                FLOAT,
    wind_gust_max           FLOAT,
    pressure                FLOAT,          -- atmospheric pressure hPa
    cloud_cover             FLOAT,          -- cloud cover %
    sunshine_duration       FLOAT,          -- sunshine duration seconds
    heat_index              FLOAT,          -- perceived temperature (derived)
    precipitation           FLOAT,
    rain_sum                FLOAT,
    dew_point               FLOAT,
    shortwave_radiation     FLOAT,
    vapour_pressure_deficit FLOAT ,
    source                  VARCHAR(20)     -- 'historical' or 'api'
);
    


-- ── Fact: Pollution Metrics ───────────────────────────────────────────────
CREATE TABLE PollutionMetrics (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    date                DATE NOT NULL,
    pm25                FLOAT,          -- fine particulates ug/m3
    pm10                FLOAT,          -- coarse particulates ug/m3
    aqi                 FLOAT,          -- US Air Quality Index
    european_aqi        FLOAT,          -- European AQI
    ozone               FLOAT,          -- surface ozone ug/m3
    nitrogen_dioxide    FLOAT,          -- NO2 ug/m3
    sulphur_dioxide     FLOAT,          -- SO2 ug/m3
    dust                FLOAT,          -- dust aerosol optical depth
    uv_index            FLOAT,          -- ultraviolet index
    pollution_level     FLOAT,          -- weighted score (derived)
    source              VARCHAR(20)     -- 'historical' or 'api'
);


ALTER TABLE dbo.PollutionMetrics ADD
    carbon_monoxide         FLOAT,
    aerosol_optical_depth   FLOAT;


-- ── Fact: Environmental Features ─────────────────────────────────────────
-- Combined and enriched dataset — feeds ML model and Power BI
CREATE TABLE dbo.EnvironmentalFeatures (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    date                DATE NOT NULL,

    -- Weather
    temperature             FLOAT,
    temp_max                FLOAT,
    temp_min                FLOAT,
    apparent_temp_max       FLOAT,
    apparent_temp_min       FLOAT,
    apparent_temp_mean      FLOAT,
    humidity                FLOAT,
    humidity_max            FLOAT,
    humidity_min            FLOAT,
    wind                    FLOAT,
    wind_max                FLOAT,
    wind_gust_max           FLOAT,
    pressure                FLOAT,
    cloud_cover             FLOAT,
    sunshine_duration       FLOAT,
    rain_sum                FLOAT,
    dew_point               FLOAT,
    shortwave_radiation     FLOAT,
    vapour_pressure_deficit FLOAT,
   
  


    -- Pollution
    pm25                FLOAT,
    pm10                FLOAT,
    aqi                 FLOAT,
    european_aqi        FLOAT,
    ozone               FLOAT,
    nitrogen_dioxide    FLOAT,
    sulphur_dioxide     FLOAT,
    dust                FLOAT,
    uv_index            FLOAT,
    precipitation       FLOAT,
    carbon_monoxide         FLOAT,
    aerosol_optical_depth   FLOAT ,

    -- Derived features (OLD)
    heat_index          FLOAT,
    pollution_level     FLOAT,
    respiratory_stress  FLOAT,
    uv_risk             FLOAT,

    -- Derived features (NEW)
    temp_range          FLOAT,
    heat_stress_peak    FLOAT,
    dust_risk_index     FLOAT,
    rain_wash_effect    FLOAT,

    -- Aether output
    health_category     VARCHAR(50),
    source              VARCHAR(20)
);

-- ── Fact: Risk Predictions ────────────────────────────────────────────────
-- ML model output stored daily
CREATE TABLE RiskPredictions (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    date                DATE NOT NULL,
    -- Input features used by model
    temperature         FLOAT,
    humidity            FLOAT,
    wind                FLOAT,
    heat_index          FLOAT,
    pm25                FLOAT,
    pm10                FLOAT,
    aqi                 FLOAT,
    pollution_level     FLOAT,
    respiratory_stress  FLOAT,
    uv_risk             FLOAT,
    -- Model output
    health_category     VARCHAR(40),    -- 5-category Aether classification
    model_version       VARCHAR(20),    -- track which model version predicted
    predicted_at        DATETIME DEFAULT GETDATE()
);

GO


ALTER TABLE RiskPredictions
ADD
    temp_range         FLOAT,
    heat_stress_peak   FLOAT,
    dust_risk_index    FLOAT,
    rain_wash_effect   FLOAT;


Go

-- ── Alter columns to match expected data types and lengths ─────────────────────────
ALTER TABLE EnvironmentalFeatures
ALTER COLUMN health_category VARCHAR(50);

ALTER TABLE RiskPredictions
ALTER COLUMN health_category VARCHAR(50);




-- ── Indexes for Power BI and ML query performance ─────────────────────────
CREATE INDEX IX_WeatherMetrics_Date        ON WeatherMetrics        (date);
CREATE INDEX IX_PollutionMetrics_Date      ON PollutionMetrics      (date);
CREATE INDEX IX_EnvironmentalFeatures_Date ON EnvironmentalFeatures  (date);
CREATE INDEX IX_RiskPredictions_Date       ON RiskPredictions        (date);
CREATE INDEX IX_RiskPredictions_Category   ON RiskPredictions        (health_category);
GO



-- ── Check for SSIS\Python Load  ─────────────────────────

Select * from PollutionMetrics
Select * from WeatherMetrics
Select * from DimDate
Select * from Environmentalfeatures
Select * from RiskPredictions



-- ── verify risk_Predication_Moodel─────────────────────────

SELECT health_category, COUNT(*) as days
FROM RiskPredictions
GROUP BY health_category
ORDER BY days DESC;



SELECT health_category, COUNT(*) as days
FROM EnvironmentalFeatures
GROUP BY health_category
ORDER BY days DESC;



-- ── verify tables ─────────────────────────

SELECT
    ef.health_category    AS rule_label,
    rp.health_category    AS model_label,
    COUNT(*)              AS days
FROM EnvironmentalFeatures ef
JOIN RiskPredictions rp ON rp.date = ef.date
GROUP BY ef.health_category, rp.health_category
ORDER BY ef.health_category, COUNT(*) DESC




SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'EnvironmentalFeatures'
ORDER BY ORDINAL_POSITION;



-- ── verify Date ─────────────────────────

SELECT MIN(date), MAX(date), COUNT(*) FROM EnvironmentalFeatures;
SELECT MIN(date), MAX(date), COUNT(*) FROM RiskPredictions;




-- ── Run in SSMS to remove today's incomplete rows   ─────────────────────────
DELETE FROM dbo.EnvironmentalFeatures WHERE source = 'api_daily';
DELETE FROM dbo.RiskPredictions       WHERE date   = CAST(GETDATE() AS DATE);