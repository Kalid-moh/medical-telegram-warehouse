{{ config(materialized='table') }}

WITH stg_msgs AS (
    SELECT * FROM {{ ref('stg_telegram_messages') }}
),

dim_channels AS (
    SELECT channel_key, channel_name FROM {{ ref('dim_channels') }}
)

SELECT
    -- 1. Unique Identifiers
    m.message_id,
    
    -- 2. Foreign Keys (Connecting to Dimensions)
    c.channel_key, 
    TO_CHAR(m.message_at, 'YYYYMMDD')::INT AS date_key,
    
    -- 3. Descriptive Attributes
    m.message_content AS message_text,
    
    -- 4. Quantitative Metrics (Facts)
    m.char_length AS message_length,
    m.view_count,
    m.forward_count,
    
    -- 5. Logic Flags
    m.is_media_attached AS has_image

FROM stg_msgs m
-- Join to get the Surrogate Key from dim_channels
INNER JOIN dim_channels c 
    ON m.channel_username = c.channel_name