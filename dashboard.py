import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# -------------------------------------------------------------
# 1. PAGE CONFIGURATION & THEME
# -------------------------------------------------------------
st.set_page_config(
    page_title="Social Media Analytics Platform",
    page_icon="",
    layout="wide"
)

st.title("Social Media Analytics Dashboard")
st.markdown("Real-time executive insights powered by **PySpark**, **PostgreSQL**, and **dbt**.")

# -------------------------------------------------------------
# 2. DATABASE CONNECTION
# -------------------------------------------------------------
@st.cache_resource
def get_db_engine():
    return create_engine("postgresql://warehouse:warehouse@localhost:5432/warehouse")

try:
    engine = get_db_engine()
except Exception as e:
    st.error(f"Error connecting to PostgreSQL database: {str(e)}")
    st.stop()

# -------------------------------------------------------------
# 3. TAB NAVIGATION (5 DATA MARTS)
# -------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "  User Engagement & Sentiment",
    "  Content Performance",
    " Hashtag Analysis",
    "  Location Analysis",
    "  Optimal Posting Window"
])

# =============================================================
# TAB 1: USER ENGAGEMENT & SENTIMENT (mart_user_engagement)
# =============================================================
with tab1:
    st.header(" User Engagement & Sentiment Analysis")
    try:
        df_user = pd.read_sql("SELECT * FROM user_engagement", engine)
        
        if df_user.empty:
            st.warning("Table 'user_engagement' is empty. Run dbt run first.")
        else:
            st.sidebar.header(" Dashboard Filters")
            gender_filter = st.sidebar.multiselect(
                "Select Gender:",
                options=df_user["gender"].unique(),
                default=df_user["gender"].unique()
            )
            age_range = st.sidebar.slider(
                "Select Age Range:",
                min_value=int(df_user["age"].min()),
                max_value=int(df_user["age"].max()),
                value=(int(df_user["age"].min()), int(df_user["age"].max()))
            )
            # Apply Filters to Data
            filtered_df = df_user[
                (df_user["gender"].isin(gender_filter)) &
                (df_user["age"].between(age_range[0], age_range[1]))
            ]

            # Executive KPI Cards
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Users", f"{len(filtered_df):,}")
            col2.metric("Total Posts", f"{filtered_df['total_posts'].sum():,}")
            col3.metric("Total Engagement Score", f"{filtered_df['total_engagement_score'].sum():,}")
            col4.metric("Avg Posts per User", f"{round(filtered_df['total_posts'].mean(), 1)}")

            st.divider()
            
            col_l, col_r = st.columns(2)
            
            # Sentiment Donut Chart
            with col_l:
                sentiment_counts = filtered_df['dominant_sentiment'].value_counts().reset_index()
                sentiment_counts.columns = ['Sentiment', 'User Count']

                fig_pie = px.pie(
                    sentiment_counts, 
                    values='User Count', 
                    names='Sentiment',
                    title='Dominant Reaction Sentiment Distribution',
                    color='Sentiment',
                    color_discrete_map={
                        'Positive': '#2ecc71',
                        'Funny / Sarcasm': '#f1c40f',
                        'Surprise / Shock': '#e67e22',
                        'Sad / Empathetic': '#3498db',
                        'Negative': '#e74c3c',
                        'No Engagement': '#95a5a6'
                    },
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # Top Creators Leaderboard
            with col_r:
                top_users = filtered_df.sort_values(by="total_engagement_score", ascending=False).head(10)
                fig_bar = px.bar(
                    top_users,
                    x="total_engagement_score",
                    y="username",
                    orientation='h',
                    color="total_posts",
                    title="Top 10 Creators by Total Engagement Score",
                    color_continuous_scale="Viridis"
                )
                fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
                
            # Demographic Scatter Plot
            st.subheader(" Demographic Analysis: Age vs. Engagement")
            fig_scatter = px.scatter(
                filtered_df[filtered_df['total_posts'] > 0],
                x="age",
                y="avg_engagement_per_post",
                color="gender",
                size="total_posts",
                hover_data=["username", "name"],
                title="User Age vs. Average Engagement per Post"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

    except Exception as e:
        st.info("Please build the `user_engagement` dbt model to populate this view.")

# =============================================================
# TAB 2: CONTENT PERFORMANCE (mart_content_performance)
# =============================================================
with tab2:
    st.header(" Content Performance & Post Length Insights")
    try:
        df_content = pd.read_sql("SELECT * FROM content_performance", engine)
        
        if df_content.empty:
            st.warning("Table 'content_performance' is empty.")
        else:
            col1, col2 = st.columns(2)
            
            # Post Length Category Breakdown
            with col1:
                length_df = df_content.groupby("post_length_category")["engagement_score"].mean().reset_index()
                fig_len = px.bar(
                    length_df,
                    x="post_length_category",
                    y="engagement_score",
                    color="post_length_category",
                    title="Average Engagement Score by Post Length Category",
                    labels={"engagement_score": "Avg Engagement Score", "post_length_category": "Length Category"}
                )
                st.plotly_chart(fig_len, use_container_width=True)
                
            # Reaction Breakdown (Love vs Wow)
            with col2:
                rx_df = df_content[['love_reactions', 'wow_reactions','angry_reactions', 'haha_reactions', 'sad_reactions', 'like_reactions', 'shares', 'comments_count']].sum().reset_index()
                rx_df.columns = ['Interaction Type', 'Total Count']
                fig_rx = px.bar(
                    rx_df,
                    x='Interaction Type',
                    y='Total Count',
                    color='Interaction Type',
                    title="Total Engagement Breakdown by Reaction & Shares"
                )
                st.plotly_chart(fig_rx, use_container_width=True)

            st.subheader(" Top 10 Most Viral Posts")
            st.dataframe(df_content.sort_values(by="engagement_score", ascending=False).head(10), use_container_width=True)

    except Exception as e:
        st.info("Please build the `content_performance` dbt model to populate this view.")

# =============================================================
# TAB 3: HASHTAG ANALYSIS (mart_tag_analysis)
# =============================================================
with tab3:
    st.header("Hashtag & Topic Trend Analysis")
    try:
        df_tags = pd.read_sql("SELECT * FROM tag_analysis ORDER BY total_posts DESC", engine)
        
        if df_tags.empty:
            st.warning("Table 'tag_analysis' is empty.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_tag_posts = px.bar(
                    df_tags.head(10),
                    x="tag",
                    y="total_posts",
                    color="total_posts",
                    title="Top 10 Hashtags by Total Post Volume"
                )
                st.plotly_chart(fig_tag_posts, use_container_width=True)
                
            with col2:
                fig_tag_eng = px.bar(
                    df_tags.sort_values(by="avg_engagement_per_post", ascending=False).head(10),
                    x="tag",
                    y="avg_engagement_per_post",
                    color="avg_engagement_per_post",
                    title="Top 10 Hashtags by Avg Engagement per Post",
                    color_continuous_scale="Magma"
                )
                st.plotly_chart(fig_tag_eng, use_container_width=True)

            st.dataframe(df_tags, use_container_width=True)

    except Exception as e:
        st.info("Please build the `tag_analysis` dbt model to populate this view.")

# =============================================================
# TAB 4: LOCATION ANALYSIS (mart_location_analysis)
# =============================================================
with tab4:
    st.header(" Geographic Location Breakdown")
    try:
        df_loc = pd.read_sql("SELECT * FROM location_analysis ORDER BY total_posts DESC", engine)
        
        if df_loc.empty:
            st.warning("Table 'location_analysis' is empty.")
        else:
            fig_loc = px.bar(
                df_loc,
                x="location",
                y="total_posts",
                color="avg_engagement_per_post",
                title="Post Volume & Avg Engagement by Geographic City/Location",
                labels={"location": "City / Location", "total_posts": "Total Posts"}
            )
            st.plotly_chart(fig_loc, use_container_width=True)
            
            st.dataframe(df_loc, use_container_width=True)

    except Exception as e:
        st.info("Please build the `location_analysis` dbt model to populate this view.")

# =============================================================
# TAB 5: OPTIMAL POSTING WINDOW (mart_time_of_day_activity)
# =============================================================
with tab5:
    st.header(" Optimal Posting Window (Time of Day Analysis)")
    try:
        # SQL Query computing hourly engagement from stg_posts
        df_time = pd.read_sql("""
            SELECT 
                EXTRACT(HOUR FROM timestamp) AS posting_hour,
                COUNT(post_id) AS total_posts,
                SUM(shares) AS total_shares,
                SUM(total_reactions) AS total_reactions,
                ROUND(AVG(total_reactions * 2 + shares * 3 + comments_count * 1)::numeric, 2) AS avg_engagement
            FROM stg_posts
            GROUP BY posting_hour
            ORDER BY posting_hour ASC
        """, engine)
        
        if df_time.empty:
            st.warning("No data found in stg_posts.")
        else:
            fig_time = px.line(
                df_time,
                x="posting_hour",
                y="avg_engagement",
                markers=True,
                title="Average Post Engagement by Hour of the Day (0 - 23)",
                labels={"posting_hour": "Hour of Day (24-Hour Clock)", "avg_engagement": "Avg Engagement Score"}
            )
            fig_time.update_traces(line_color='#e74c3c', line_width=3)
            st.plotly_chart(fig_time, use_container_width=True)

            st.dataframe(df_time, use_container_width=True)

    except Exception as e:
        st.info("Please ensure `stg_posts` table is loaded in PostgreSQL.")
