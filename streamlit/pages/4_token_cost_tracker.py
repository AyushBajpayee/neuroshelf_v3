import streamlit as st
import sys
sys.path.append('..')
from common import get_db_connection, render_sidebar
import pandas as pd
import plotly.express as px

render_sidebar(show_navigation=False, key_prefix="token_tracker")

st.title("💰 Token Usage & Cost Tracker")
st.markdown("---")

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    cursor.execute("SELECT SUM(estimated_cost) FROM token_usage WHERE timestamp >= NOW() - INTERVAL '24 hours'")
    daily_cost = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(estimated_cost) FROM token_usage WHERE timestamp >= NOW() - INTERVAL '7 days'")
    weekly_cost = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(total_tokens) FROM token_usage")
    total_tokens = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(DISTINCT agent_name) FROM token_usage")
    agent_count = cursor.fetchone()[0] or 0

    with col1:
        st.metric("24h Cost", f"${daily_cost:.4f}")

    with col2:
        st.metric("7d Cost", f"${weekly_cost:.4f}")

    with col3:
        st.metric("Total Tokens", f"{total_tokens:,}")

    with col4:
        st.metric("Active Agents", agent_count)

    st.markdown("---")

    # Cost by agent
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Cost by Agent (Last 7 Days)")
        cursor.execute("""
            SELECT
                agent_name,
                SUM(estimated_cost) as cost,
                COUNT(*) as operations,
                SUM(total_tokens) as tokens
            FROM token_usage
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            GROUP BY agent_name
            ORDER BY cost DESC
        """)
        agent_costs = cursor.fetchall()

        if agent_costs:
            df = pd.DataFrame(agent_costs, columns=["Agent", "Cost", "Operations", "Tokens"])
            fig = px.bar(df, x="Agent", y="Cost", title="Cost by Agent")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Cost Over Time")
        cursor.execute("""
            SELECT
                DATE(timestamp) as date,
                SUM(estimated_cost) as cost
            FROM token_usage
            WHERE timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(timestamp)
            ORDER BY date
        """)
        daily_costs = cursor.fetchall()

        if daily_costs:
            df = pd.DataFrame(daily_costs, columns=["Date", "Cost"])
            fig = px.line(df, x="Date", y="Cost", title="Daily Cost Trend")
            st.plotly_chart(fig, use_container_width=True)

    # Recent operations
    st.subheader("Recent Operations")
    cursor.execute("""
        SELECT
            timestamp,
            agent_name,
            operation,
            total_tokens,
            estimated_cost
        FROM token_usage
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    recent = cursor.fetchall()

    if recent:
        df = pd.DataFrame(recent, columns=["Timestamp", "Agent", "Operation", "Tokens", "Cost"])
        st.dataframe(df, use_container_width=True)

    cursor.close()
    conn.close()

except Exception as e:
    st.error(f"Error: {e}")
