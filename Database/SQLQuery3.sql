USE [AetherDW_V0]
GO

/****** Object:  View [dbo].[vw_LatestForecast]    Script Date: 26/05/09 5:01:06 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


ALTER VIEW [dbo].[vw_LatestForecast] AS
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY forecast_date, forecast_horizon
               ORDER BY generated_at DESC
           ) AS rn
    FROM gold.ForecastPredictions
)
SELECT
    forecast_date,
    forecast_horizon,
    predicted_category,
    confidence,

    -- NEW features
    temp_range,
    heat_stress_peak,
    dust_risk_index,
    rain_wash_effect,

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


