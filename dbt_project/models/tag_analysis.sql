SELECT 
    t.tag,
    COUNT(DISTINCT t.post_id) AS total_posts,
    SUM(p.shares) AS total_shares,
    SUM(p.total_reactions) AS total_reactions,
    SUM(p.comments_count) AS total_comments,
    ROUND(AVG(p.total_reactions * 2 + p.shares * 3 + p.comments_count * 1)::numeric, 2) AS avg_engagement_per_post
FROM {{ source('public', 'stg_post_tags') }} t
JOIN {{ source('public', 'stg_posts') }} p ON t.post_id = p.post_id
GROUP BY t.tag
ORDER BY total_posts DESC
