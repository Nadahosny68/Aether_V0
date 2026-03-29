-- ============================================================
-- Aether · Power BI DAX measures for ForecastPredictions
-- Paste each block into the DAX formula bar
-- ============================================================


-- ── Page 3: 3-day forecast ────────────────────────────────────────────────────

-- Tomorrow's predicted category (horizon = 1)
Tomorrow's Category =
VAR _tomorrow =
    CALCULATE(
        SELECTEDVALUE(ForecastPredictions[predicted_category]),
        ForecastPredictions[forecast_horizon] = 1
    )
RETURN IF(ISBLANK(_tomorrow), "No forecast available", _tomorrow)


-- Day +2 predicted category
Day +2 Category =
VAR _day2 =
    CALCULATE(
        SELECTEDVALUE(ForecastPredictions[predicted_category]),
        ForecastPredictions[forecast_horizon] = 2
    )
RETURN IF(ISBLANK(_day2), "No forecast available", _day2)


-- Day +3 predicted category
Day +3 Category =
VAR _day3 =
    CALCULATE(
        SELECTEDVALUE(ForecastPredictions[predicted_category]),
        ForecastPredictions[forecast_horizon] = 3
    )
RETURN IF(ISBLANK(_day3), "No forecast available", _day3)


-- Confidence as a formatted percentage for display cards
Forecast Confidence (D+1) =
VAR _conf =
    CALCULATE(
        AVERAGE(ForecastPredictions[confidence]),
        ForecastPredictions[forecast_horizon] = 1
    )
RETURN FORMAT(_conf, "0%")


-- Forecast AQI for each horizon (for trend mini-chart)
Forecast AQI D+1 =
    CALCULATE(AVERAGE(ForecastPredictions[aqi]), ForecastPredictions[forecast_horizon] = 1)

Forecast AQI D+2 =
    CALCULATE(AVERAGE(ForecastPredictions[aqi]), ForecastPredictions[forecast_horizon] = 2)

Forecast AQI D+3 =
    CALCULATE(AVERAGE(ForecastPredictions[aqi]), ForecastPredictions[forecast_horizon] = 3)


-- Worst day in the 3-day window (for headline alert card)
Worst Forecast Category =
VAR _tbl =
    ADDCOLUMNS(
        VALUES(ForecastPredictions[predicted_category]),
        "Severity",
        SWITCH(
            ForecastPredictions[predicted_category],
            "Safe Air Day",                5,
            "Moderate Risk Day",           4,
            "High Respiratory Risk Day",   3,
            "Mask Recommended Day",        2,
            "Avoid Outdoor Activity Day",  1,
            6
        )
    )
RETURN MINX(_tbl, [Severity])
-- (lower number = more severe; use in conditional card formatting)


-- Health advice for the forecast card (driven by D+1 prediction)
Forecast Health Advice =
SWITCH(
    [Tomorrow's Category],
    "Safe Air Day",
        "Good air quality expected. Outdoor activity is safe.",
    "Moderate Risk Day",
        "Air quality will be moderate. Sensitive groups should limit prolonged outdoor exertion.",
    "High Respiratory Risk Day",
        "Elevated pollution forecast. Reduce outdoor activity, especially in the morning.",
    "Mask Recommended Day",
        "Poor air quality expected. Wear an N95 mask outdoors and keep windows closed.",
    "Avoid Outdoor Activity Day",
        "Hazardous conditions forecast. Stay indoors and use air purification if available.",
    "Forecast data unavailable."
)


-- Forecast PM2.5 for display (D+1)
Forecast PM2.5 (D+1) =
    CALCULATE(
        ROUND(AVERAGE(ForecastPredictions[pm25]), 1),
        ForecastPredictions[forecast_horizon] = 1
    )


-- Forecast heat index for display (D+1)
Forecast Heat Index (D+1) =
    CALCULATE(
        ROUND(AVERAGE(ForecastPredictions[heat_index]), 1),
        ForecastPredictions[forecast_horizon] = 1
    )


-- Days until next Safe Air Day in the forecast window
Days Until Safe Air =
VAR _safe =
    CALCULATE(
        MIN(ForecastPredictions[forecast_horizon]),
        ForecastPredictions[predicted_category] = "Safe Air Day"
    )
RETURN
    IF(
        ISBLANK(_safe),
        "None in 3-day window",
        "Day +" & _safe
    )


-- ── Relationship note ─────────────────────────────────────────────────────────
--
-- ForecastPredictions connects to DimDate via forecast_date → date
-- Cardinality: Many to One (ForecastPredictions → DimDate)
-- Cross-filter: Single
--
-- Do NOT create a direct relationship to RiskPredictions or
-- EnvironmentalFeatures — bridge through DimDate only.
-- ─────────────────────────────────────────────────────────────────────────────