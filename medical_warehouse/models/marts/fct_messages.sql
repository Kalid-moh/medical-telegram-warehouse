{{ config(materialized='table') }}

WITH stg_msgs AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
),

dim_channels AS (
    -- Reference dim_channels to create DAG dependency
    SELECT channel_key, channel_name FROM {{ ref('dim_channels') }}
),

dim_dates AS (
    -- Reference dim_dates to create the missing link in your DAG
    SELECT date_key, full_date FROM {{ ref('dim_dates') }}
)

SELECT
    -- 1. Unique Identifiers
    m.message_id,
    
    -- 2. Foreign Keys (Connecting to Dimensions)
    c.channel_key, 
    d.date_key,
    
    -- 3. Descriptive Attributes
    m.message_content AS message_text,
    
    -- 4. Quantitative Metrics (Facts)
    m.char_length AS message_length,
    m.view_count,
    m.forward_count,
    
    -- 5. Logic Flags
    m.is_media_attached AS has_image

FROM stg_msgs m
-- Join with Channels to get the Surrogate Key
INNER JOIN dim_channels c 
    ON m.channel_username = c.channel_name
-- Join with Dates using the calculated date key to enforce the DAG relationship
INNER JOIN dim_dates d 
    ON TO_CHAR(m.message_at, 'YYYYMMDD')::INT = d.date_key