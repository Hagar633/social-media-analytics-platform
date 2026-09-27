SELECT 
    EXTRACT(HOUR FROM p.timestamp) AS posting_hour,
    TO_CHAR(p.timestamp, 'Day') AS day_of_week,
    COUNT(p.post_id) AS total_posts,
    ROUND(AVG(p.total_reactions + p.shares * 2)::numeric, 2) AS avg_engagement
FROM {{ source('public', 'stg_posts') }} p
GROUP BY posting_hour, day_of_week
ORDER BY avg_engagement DESC
