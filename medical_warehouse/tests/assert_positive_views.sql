-- This test returns rows where view_count is less than 0.
-- If it returns 0 rows, the test passes.

SELECT
    message_id,
    view_count
FROM {{ ref('fct_messages') }}
WHERE view_count < 0