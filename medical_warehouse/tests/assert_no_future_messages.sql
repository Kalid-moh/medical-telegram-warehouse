-- This test returns rows where the message date is in the future.
-- If it returns 0 rows, the test passes.

SELECT
    message_id,
    message_at
FROM {{ ref('stg_telegram_messages') }}
WHERE message_at > CURRENT_TIMESTAMP