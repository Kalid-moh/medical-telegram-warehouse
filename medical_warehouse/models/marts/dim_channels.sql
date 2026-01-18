{{ config(materialized='table') }}


-- models/marts/dim_channels.sql
WITH channel_stats AS (
    SELECT
        channel_username,
        MIN(message_at) AS first_post_date,
        MAX(message_at) AS last_post_date,
        COUNT(message_id) AS total_posts,
        AVG(view_count) AS avg_views
    FROM {{ ref('stg_telegram_messages') }}
    GROUP BY 1
)

SELECT
    -- Generate a surrogate key using MD5 hash of the unique username
    MD5(channel_username) AS channel_key,
    channel_username AS channel_name,
    
    -- Categorization logic based on name patterns
    CASE 
        WHEN channel_username ILIKE '%pharma%' OR channel_username ILIKE '%med%' THEN 'Pharmaceutical'
        WHEN channel_username ILIKE '%cosm%' OR channel_username ILIKE '%beauty%' THEN 'Cosmetics'
        ELSE 'Medical'
    END AS channel_type,
    
    first_post_date,
    last_post_date,
    total_posts,
    CAST(avg_views AS DECIMAL(10,2)) AS avg_views
FROM channel_stats