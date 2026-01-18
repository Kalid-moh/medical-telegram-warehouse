{{ config(materialized='table') }}


-- models/staging/stg_telegram_messages.sql

WITH raw_data AS (
    SELECT * FROM {{ source('raw', 'telegram_messages') }}
)

SELECT
    -- 1. Standardize IDs and Foreign Keys
    CAST(message_id AS BIGINT) AS message_id,
    channel_username,
    channel_title,

    -- 2. Cast Data Types
    CAST(date AS TIMESTAMP WITH TIME ZONE) AS message_at,
    
    -- 3. Clean Text Data
    TRIM(text) AS message_content,
    
    -- 4. Handle Numeric Fields
    COALESCE(views, 0) AS view_count,
    COALESCE(forwards, 0) AS forward_count,
    
    -- 5. Logic/Flags
    has_media AS is_media_attached,
    image_path,
    
    -- 6. Calculated Fields (Feature Engineering)
    LENGTH(text) AS char_length,
    CARDINALITY(REGEXP_SPLIT_TO_ARRAY(TRIM(text), '\s+')) AS word_count,
    
    -- Metadata
    loaded_at AS ingested_at,
    CURRENT_TIMESTAMP AS transformed_at

FROM raw_data
WHERE message_id IS NOT NULL 
  AND text IS NOT NULL -- Remove empty/invalid system messages