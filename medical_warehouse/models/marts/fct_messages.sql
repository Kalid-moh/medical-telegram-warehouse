{{ config(materialized='table') }}

WITH stg_msgs AS (
    -- Reference the staging layer
    SELECT * FROM {{ ref('stg_telegram_messages') }}
),

dim_channels AS (
    -- Reference dim_channels to create the DAG link
    SELECT channel_key, channel_name FROM {{ ref('dim_channels') }}
),

dim_dates AS (
    -- Reference dim_dates to link the independent date dimension to the fact
    SELECT date_key FROM {{ ref('dim_dates') }}
)

SELECT
    -- 1. Identifiers
    m.message_id,
    
    -- 2. Foreign Keys (connecting to Dimension Tables)
    c.channel_key, 
    d.date_key,
    
    -- 3. Descriptive Attributes
    m.message_content AS message_text,
    
    -- 4. Quantitative Metrics (The Facts)
    m.char_length AS message_length,
    m.view_count,
    m.forward_count,
    
    -- 5. Logic Flags
    m.is_media_attached AS has_image

FROM stg_msgs m
-- Join to get the Surrogate Key for the channel
INNER JOIN dim_channels c 
    ON m.channel_username = c.channel_name
-- Join to ensure every message date exists in our dim_dates table
INNER JOIN dim_dates d 
    ON TO_CHAR(m.message_at, 'YYYYMMDD')::INT = d.date_key