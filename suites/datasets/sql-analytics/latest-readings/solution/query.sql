WITH ranked AS (
    SELECT site, value,
           ROW_NUMBER() OVER (PARTITION BY site ORDER BY minute DESC, id DESC) AS position
    FROM readings
    WHERE value IS NOT NULL
)
SELECT site, value FROM ranked WHERE position = 1 ORDER BY site;
