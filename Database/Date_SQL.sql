USE AetherDW_V0;

INSERT INTO DimDate (date, year, month, month_name, quarter, week, day_of_week, is_weekend)
SELECT DISTINCT
    CAST(date AS DATE),
    YEAR(CAST(date AS DATE)),
    MONTH(CAST(date AS DATE)),
    DATENAME(MONTH, CAST(date AS DATE)),
    DATEPART(QUARTER, CAST(date AS DATE)),
    DATEPART(WEEK, CAST(date AS DATE)),
    DATENAME(WEEKDAY, CAST(date AS DATE)),
    CASE WHEN DATEPART(WEEKDAY, CAST(date AS DATE)) IN (1,7) THEN 1 ELSE 0 END
FROM EnvironmentalFeatures
WHERE date IS NOT NULL;