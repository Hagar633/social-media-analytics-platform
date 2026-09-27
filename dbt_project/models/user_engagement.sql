WITH user_posts AS (
    SELECT 
        u.user_id,
        u.username,
        u.name,
        u.age,
        u.gender,
        COUNT(p.post_id) AS total_posts,
        COALESCE(SUM(p.shares), 0) AS total_shares,
        COALESCE(SUM(p.like_reactions), 0) AS total_like,
        COALESCE(SUM(p.love_reactions), 0) AS total_love,
        COALESCE(SUM(p.haha_reactions), 0) AS total_haha,
        COALESCE(SUM(p.wow_reactions), 0) AS total_wow,
        COALESCE(SUM(p.sad_reactions), 0) AS total_sad,
        COALESCE(SUM(p.angry_reactions), 0) AS total_angry,
        COALESCE(SUM(p.total_reactions), 0) AS total_reactions,
        COALESCE(SUM(p.comments_count), 0) AS total_comments
    FROM {{ source('public', 'stg_users') }} u
    LEFT JOIN {{ source('public', 'stg_posts') }} p ON u.user_id = p.user_id
    GROUP BY u.user_id, u.username, u.name, u.age, u.gender
),
user_metrics AS (
    SELECT 
        *,
        (total_reactions * 2 + total_shares * 3 + total_comments * 1) AS total_engagement_score,
        CASE 
            WHEN total_posts > 0 THEN ROUND((total_reactions * 2 + total_shares * 3 + total_comments * 1)::numeric / total_posts, 2)
            ELSE 0 
        END AS avg_engagement_per_post,
        -- Find the maximum count value across all 6 reaction types
        GREATEST(total_like, total_love, total_haha, total_wow, total_sad, total_angry) AS max_reaction_count
    FROM user_posts
)
SELECT 
    user_id,
    username,
    name,
    age,
    gender,
    total_posts,
    total_shares,
    total_like,
    total_love,
    total_haha,
    total_wow,
    total_sad,
    total_angry,
    total_reactions,
    total_comments,
    total_engagement_score,
    avg_engagement_per_post,

    
    CASE 
        WHEN total_reactions = 0 THEN 'None'
        WHEN max_reaction_count = total_love  THEN 'Love'
        WHEN max_reaction_count = total_like  THEN 'Like'
        WHEN max_reaction_count = total_haha  THEN 'Haha'
        WHEN max_reaction_count = total_wow   THEN 'Wow'
        WHEN max_reaction_count = total_sad   THEN 'Sad'
        WHEN max_reaction_count = total_angry THEN 'Angry'
        ELSE 'None'
    END AS dominant_reaction_type,

    
    CASE 
        WHEN total_reactions = 0 THEN 'No Engagement'
        WHEN max_reaction_count IN (total_love, total_like) THEN 'Positive'
        WHEN max_reaction_count = total_haha                THEN 'Funny / Sarcasm'
        WHEN max_reaction_count = total_wow                 THEN 'Surprise / Shock'
        WHEN max_reaction_count = total_sad                 THEN 'Sad / Empathetic'
        WHEN max_reaction_count = total_angry               THEN 'Negative'
        ELSE 'Neutral'
    END AS dominant_sentiment

FROM user_metrics
