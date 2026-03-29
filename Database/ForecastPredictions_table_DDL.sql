-- ============================================================
-- Aether · ForecastPredictions table
-- Run against AetherDW_V0 after the existing DDL.sql
-- ============================================================

IF OBJECT_ID('dbo.ForecastPredictions', 'U') IS NOT NULL
    DROP TABLE dbo.ForecastPredictions;

CREATE TABLE dbo.ForecastPredictions (
    id                  INT IDENTITY(1,1) PRIMARY KEY,

    -- Forecast metadata
    forecast_date       DATE        NOT NULL,   -- the day being predicted
    forecast_horizon    TINYINT     NOT NULL,   -- 1 = tomorrow, 2 = day after, 3 = day +3
    generated_at        DATETIME    NOT NULL DEFAULT GETDATE(),
    model_version       VARCHAR(20) NOT NULL,

    -- Weather forecast inputs
    temperature         FLOAT,
    humidity            FLOAT,
    wind                FLOAT,
    pressure            FLOAT,
    cloud_cover         FLOAT,

    -- Pollution forecast inputs
    pm25                FLOAT,
    pm10                FLOAT,
    aqi                 FLOAT,
    ozone               FLOAT,
    nitrogen_dioxide    FLOAT,
    sulphur_dioxide     FLOAT,

    -- Engineered features
    heat_index          FLOAT,
    pollution_level     FLOAT,
    respiratory_stress  FLOAT,
    uv_risk             FLOAT,

    -- Prediction output
    predicted_category  VARCHAR(60) NOT NULL,
    confidence          FLOAT,           -- max class probability from RF

    -- Confidence breakdown (all 5 classes)
    prob_safe           FLOAT,
    prob_moderate       FLOAT,
    prob_high_resp      FLOAT,
    prob_mask           FLOAT,
    prob_avoid          FLOAT,

    CONSTRAINT uq_forecast_date_horizon
        UNIQUE (forecast_date, forecast_horizon, model_version)
);

-- Index for dashboard queries (latest forecast for a given date)
CREATE NONCLUSTERED INDEX ix_forecast_date
    ON dbo.ForecastPredictions (forecast_date, forecast_horizon)
    INCLUDE (predicted_category, confidence, generated_at);

-- ============================================================
-- Helper view: latest 3-day window (always the most recent run)
-- ============================================================
IF OBJECT_ID('dbo.vw_LatestForecast', 'V') IS NOT NULL
    DROP VIEW dbo.vw_LatestForecast;
GO

CREATE VIEW dbo.vw_LatestForecast AS
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY forecast_date, forecast_horizon
               ORDER BY generated_at DESC
           ) AS rn
    FROM dbo.ForecastPredictions
)
SELECT
    forecast_date,
    forecast_horizon,
    predicted_category,
    confidence,
    prob_safe,
    prob_moderate,
    prob_high_resp,
    prob_mask,
    prob_avoid,
    temperature,
    humidity,
    wind,
    pm25,
    aqi,
    heat_index,
    pollution_level,
    respiratory_stress,
    generated_at,
    model_version
FROM ranked
WHERE rn = 1;
GO




-- ============================================================
-- check: latest 3-day 
-- ============================================================

SELECT forecast_date, forecast_horizon, predicted_category, confidence, generated_at
FROM ForecastPredictions
ORDER BY forecast_date;