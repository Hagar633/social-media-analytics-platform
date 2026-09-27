import sys
import logging

import psycopg2
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, coalesce, lit, size, to_timestamp

# Initialize Spark Session with JDBC Driver 
spark = SparkSession.builder \
    .appName("SocialMediaETL") \
    .config("spark.jars", "/home/jovyan/drivers/postgresql-42.7.3.jar") \
    .getOrCreate()

# Read raw multiline JSON after it was added inside the docker container
json_path = "/home/jovyan/datasets/social_media_info.json"
raw_df = spark.read.option("multiline", "true").json(json_path)
raw_df.printSchema()





#creating users_df by selecting relevant columns, casting age to integer, converting date_created to timestamp,
#  filtering out null user_ids, and dropping duplicates based on user_id
users_df = raw_df.select(
    col("user_id"),
    col("username"),
    col("email"),
    col("age").cast("integer").alias("age"),
    col("gender"),
    col("name"),
    to_timestamp(col("date_created")).alias("date_created")
).filter(col("user_id").isNotNull()).dropDuplicates(["user_id"])



# the posts table is created by exploding the nested posts array, extracting relevant fields,
#  computing derived metrics (like total reactions and comments count), filtering out null post_ids, 
# and dropping duplicates based on post_id.

# Explode the nested posts array
posts_exploded = raw_df.filter(col("posts").isNotNull()) \
    .select(col("user_id"), explode(col("posts")).alias("post"))

# Extract fields & compute derived metrics (reactions & comments count)
love_col = coalesce(col("post.reactions.love"), lit(0))
wow_col = coalesce(col("post.reactions.wow"), lit(0))
angry_col = coalesce(col("post.reactions.angry"), lit(0))
sad_col = coalesce(col("post.reactions.sad"), lit(0))
like_col = coalesce(col("post.reactions.like"), lit(0))
haha_col = coalesce(col("post.reactions.haha"), lit(0))
shares_col = coalesce(col("post.shares").cast("integer"), lit(0))
comments_cnt = coalesce(size(col("post.comments")), lit(0))

posts_df = posts_exploded.select(
    col("post.post_id").alias("post_id"),
    col("user_id").alias("user_id"),
    col("post.post_text").alias("post_text"),
    to_timestamp(col("post.timestamp")).alias("timestamp"),
    col("post.location").alias("location"),
    shares_col.alias("shares"),
    love_col.alias("love_reactions"),
    wow_col.alias("wow_reactions"),
    angry_col.alias("angry_reactions"),
    sad_col.alias("sad_reactions"),
    like_col.alias("like_reactions"),
    haha_col.alias("haha_reactions"),
    (love_col + wow_col + angry_col + sad_col + like_col + haha_col).alias("total_reactions"),
    comments_cnt.alias("comments_count")
).filter(col("post_id").isNotNull()).dropDuplicates(["post_id"])




# since tags has texts, we can explode the tags array and create a separate table for tags associated with each post.
tags_exploded = posts_exploded.filter(col("post.tags").isNotNull()) \
    .select(
        col("post.post_id").alias("post_id"),
        explode(col("post.tags")).alias("tag")
    ).filter(col("post_id").isNotNull() & col("tag").isNotNull()) \
    .dropDuplicates(["post_id", "tag"])




 #since also comments has their specs, it was exploded and a separate table was created for comments associated with each post, extracting relevant fields and filtering out null post_ids.
comments_exploded = posts_exploded.filter(col("post.comments").isNotNull()) \
    .select(
        col("post.post_id").alias("post_id"),
        explode(col("post.comments")).alias("comment")
    )

comments_df = comments_exploded.select(
    col("post_id").alias("post_id"),
    col("comment.user_id").alias("comment_user_id"),
    col("comment.comment").alias("comment_text"),
    to_timestamp(col("comment.timestamp")).alias("timestamp")
).filter(col("post_id").isNotNull())




## Write DataFrames to PostgreSQL using JDBC
jdbc_url = "jdbc:postgresql://postgres_dw:5432/warehouse"
db_properties = {
    "user": "warehouse",
    "password": "warehouse",
    "driver": "org.postgresql.Driver"
}

users_df.write.jdbc(jdbc_url, "temp_stg_users", mode="overwrite", properties=db_properties)
posts_df.write.jdbc(jdbc_url, "temp_stg_posts", mode="overwrite", properties=db_properties)
tags_exploded.write.jdbc(jdbc_url, "temp_stg_post_tags", mode="overwrite", properties=db_properties)
comments_df.write.jdbc(jdbc_url, "temp_stg_comments", mode="overwrite", properties=db_properties)


# Connect to PostgreSQL and Execute Upsert (ON CONFLICT) Statements, first connection was to read a file into a dataframe using the 
# driver and write into postgres, 
# this one is to connect to postgres itself to do update on it not from json to dataframes

conn = psycopg2.connect(
    host="postgres_dw",
    database="warehouse",
    user="warehouse",
    password="warehouse"
)
cursor = conn.cursor()

#  stg_users UPSERT
cursor.execute("""
    INSERT INTO stg_users (user_id, username, email, age, gender, name, date_created)
    SELECT user_id, username, email, age, gender, name, date_created FROM temp_stg_users
    ON CONFLICT (user_id) 
    DO UPDATE SET 
        username = EXCLUDED.username,
        email = EXCLUDED.email,
        age = EXCLUDED.age,
        gender = EXCLUDED.gender,
        name = EXCLUDED.name,
        date_created = EXCLUDED.date_created;
""")
#  stg_posts UPSERT 
cursor.execute("""
    INSERT INTO stg_posts (post_id, user_id, post_text, timestamp, location, shares, 
                            love_reactions, wow_reactions, angry_reactions, sad_reactions, 
                            like_reactions, haha_reactions, total_reactions, comments_count)
    SELECT post_id, user_id, post_text, timestamp, location, shares, 
           love_reactions, wow_reactions, angry_reactions, sad_reactions, 
           like_reactions, haha_reactions, total_reactions, comments_count 
    FROM temp_stg_posts
    ON CONFLICT (post_id) 
    DO UPDATE SET 
        post_text = EXCLUDED.post_text,
        location = EXCLUDED.location,
        shares = EXCLUDED.shares,
        love_reactions = EXCLUDED.love_reactions,
        wow_reactions = EXCLUDED.wow_reactions,
        angry_reactions = EXCLUDED.angry_reactions,
        sad_reactions = EXCLUDED.sad_reactions,
        like_reactions = EXCLUDED.like_reactions,
        haha_reactions = EXCLUDED.haha_reactions,
        total_reactions = EXCLUDED.total_reactions,
        comments_count = EXCLUDED.comments_count;
""")
#  stg_post_tags UPSERT ---
cursor.execute("""
    INSERT INTO stg_post_tags (post_id, tag)
    SELECT post_id, tag FROM temp_stg_post_tags
    ON CONFLICT (post_id, tag) 
    DO NOTHING;
""")
# stg_comments UPSERT  ---
cursor.execute("""
    INSERT INTO stg_comments (post_id, comment_user_id, comment_text, timestamp)
    SELECT post_id, comment_user_id, comment_text, timestamp FROM temp_stg_comments
    ON CONFLICT (post_id, comment_user_id, timestamp) 
    DO NOTHING;
""")
# Commit transactions & cleanup temporary tables
conn.commit()
cursor.execute("DROP TABLE temp_stg_users, temp_stg_posts, temp_stg_post_tags, temp_stg_comments;")
conn.commit()
cursor.close()
conn.close()
print("Incremental update done")