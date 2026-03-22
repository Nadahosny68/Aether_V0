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
    humidity            FLOAT,          -- relative humidity %
    wind                FLOAT,          -- wind speed m/s
    pressure            FLOAT,          -- atmospheric pressure hPa
    cloud_cover         FLOAT,          -- cloud cover %
    sunshine_duration   FLOAT,          -- sunshine duration seconds
    heat_index          FLOAT,          -- perceived temperature (derived)
    source              VARCHAR(20)     -- 'historical' or 'api'
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

-- ── Fact: Environmental Features ─────────────────────────────────────────
-- Combined and enriched dataset — feeds ML model and Power BI
CREATE TABLE EnvironmentalFeatures (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    date                DATE NOT NULL,
    -- Weather
    temperature         FLOAT,
    humidity            FLOAT,
    wind                FLOAT,
    pressure            FLOAT,
    cloud_cover         FLOAT,
    sunshine_duration   FLOAT,
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
    -- Derived features
    heat_index          FLOAT,
    pollution_level     FLOAT,
    respiratory_stress  FLOAT,
    uv_risk             FLOAT,
    -- Aether output
    health_category     VARCHAR(40),
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

