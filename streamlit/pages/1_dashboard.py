import streamlit as st
import sys
sys.path.append('..')
from app import get_db_connection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Analytics Dashboard")
st.markdown("---")

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Promotion performance over time
    st.subheader("Promotion Performance Trends")
    cursor.execute("""
        SELECT
            DATE(created_at) as date,
            COUNT(*) as promotions_created,
            SUM(actual_revenue) as revenue,
            AVG(margin_percent) as avg_margin
        FROM promotions
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    trend_data = cursor.fetchall()
    if trend_data:
        df = pd.DataFrame(trend_data, columns=["date", "promotions", "revenue", "avg_margin"])
        fig = px.line(df, x="date", y="revenue", title="Daily Revenue from Promotions")
        st.plotly_chart(fig, use_container_width=True)

    cursor.close()
    conn.close()

except Exception as e:
    st.error(f"Error: {e}")
