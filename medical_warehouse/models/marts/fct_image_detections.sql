{{ config(
    materialized='table'
) }}


with message as(
    select 
    message_id,
    channel_key,
    date_key
    from {{ ref('fct_messages') }}
),
yolo_detections as(
    select 
    message_id,
    detected_class,
    confidence_score,
    image_category

    from {{ ref('yolo_detections') }}
)

select 
m.message_id,
m.channel_key,
m.date_key,
y.detected_class,
y.confidence_score,
y.image_category
from message m
join yolo_detections y
on m.message_id = y.message_id