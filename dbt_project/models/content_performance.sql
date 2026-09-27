SELECT 
    p.post_id,
    p.user_id,
    p.timestamp AS post_timestamp,
    p.location,
    p.shares,
    p.love_reactions,
    p.wow_reactions,
    p.angry_reactions,
    p.haha_reactions,
    p.sad_reactions,
    p.like_reactions,
    p.total_reactions,
    p.comments_count,
    LENGTH(p.post_text) AS post_length_chars,
    CASE 
        WHEN LENGTH(p.post_text) < 50 THEN 'Short (< 50 chars)'
        WHEN LENGTH(p.post_text) BETWEEN 50 AND 150 THEN 'Medium (50-150 chars)'
        ELSE 'Long (> 150 chars)'
    END AS post_length_category,
    (p.total_reactions * 2 + p.shares * 3 + p.comments_count * 1) AS engagement_score
FROM {{ source('public', 'stg_posts') }} p
