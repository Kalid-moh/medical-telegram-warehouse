{{ config(materialized='table') }}

WITH date_series AS (
    -- Generates dates from today (Jan 18) to Wednesday (Jan 21)
    SELECT 
        datum::date AS full_date
    FROM generate_series(
        '2006-01-01'::date, 
        '2026-01-21'::date, 
        '1 day'::interval
    ) AS datum
)

SELECT
    -- Date key (e.g., 20260118)
    TO_CHAR(full_date, 'YYYYMMDD')::INT AS date_key,
    full_date,
    
    -- Day details
    TO_CHAR(full_date, 'Day') AS day_name,
    EXTRACT(DOW FROM full_date) AS day_of_week, -- 0 for Sunday
    
    -- Calendar parts
    EXTRACT(WEEK FROM full_date) AS week_of_year,
    EXTRACT(MONTH FROM full_date) AS month,
    TO_CHAR(full_date, 'Month') AS month_name,
    EXTRACT(QUARTER FROM full_date) AS quarter,
    EXTRACT(YEAR FROM full_date) AS year,
    
    -- Boolean flag for weekends
    CASE 
        WHEN EXTRACT(DOW FROM full_date) IN (0, 6) THEN TRUE 
        ELSE FALSE 
    END AS is_weekend

FROM date_series