import streamlit as st
import sys
sys.path.append('..')
from common import get_db_connection, render_sidebar
import pandas as pd
import plotly.express as px

render_sidebar(show_navigation=False, key_prefix="analytics")

st.title("📈 Analytics & Insights")
st.markdown("---")

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Agent Decisions
    st.subheader("Agent Decision Log")
    cursor.execute("""
        SELECT
            created_at,
            agent_name,
            decision_type,
            LEFT(reasoning, 100) as reasoning_preview,
            decision_outcome
        FROM agent_decisions
        ORDER BY created_at DESC
        LIMIT 20
    """)
    decisions = cursor.fetchall()

    if decisions:
        df = pd.DataFrame(decisions, columns=["Timestamp", "Agent", "Decision Type", "Reasoning", "Outcome"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No agent decisions logged yet")

    st.markdown("---")

    # Promotion Performance Analysis
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Promotion Performance Distribution")
        cursor.execute("""
            SELECT
                CASE
                    WHEN (actual_units_sold::float / NULLIF(expected_units_sold, 0)) >= 1.5 THEN 'Excellent (150%+)'
                    WHEN (actual_units_sold::float / NULLIF(expected_units_sold, 0)) >= 1.0 THEN 'Good (100-150%)'
                    WHEN (actual_units_sold::float / NULLIF(expected_units_sold, 0)) >= 0.7 THEN 'Acceptable (70-100%)'
                    ELSE 'Poor (<70%)'
                END as performance_category,
                COUNT(*) as count
            FROM promotions
            WHERE status IN ('completed', 'retracted')
              AND expected_units_sold > 0
            GROUP BY performance_category
        """)
        perf_dist = cursor.fetchall()

        if perf_dist:
            df = pd.DataFrame(perf_dist, columns=["Performance", "Count"])
            fig = px.pie(df, values="Count", names="Performance", title="Performance Distribution")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Margin Distribution")
        cursor.execute("""
            SELECT
                CASE
                    WHEN margin_percent >= 25 THEN '25%+'
                    WHEN margin_percent >= 20 THEN '20-25%'
                    WHEN margin_percent >= 15 THEN '15-20%'
                    WHEN margin_percent >= 10 THEN '10-15%'
                    ELSE '<10%'
                END as margin_range,
                COUNT(*) as count
            FROM promotions
            WHERE status IN ('completed', 'retracted')
            GROUP BY margin_range
            ORDER BY margin_range DESC
        """)
        margin_dist = cursor.fetchall()

        if margin_dist:
            df = pd.DataFrame(margin_dist, columns=["Margin Range", "Count"])
            fig = px.bar(df, x="Margin Range", y="Count", title="Margin Distribution")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Promotion ROI
    # st.subheader("Promotion ROI Analysis")
    # cursor.execute("""
    #     SELECT
    #         p.promotion_code,
    #         s.name as sku,
    #         p.actual_revenue,
    #         COALESCE(SUM(t.estimated_cost), 0) as agent_cost,
    #         p.actual_revenue - COALESCE(SUM(t.estimated_cost), 0) as net_revenue,
    #         CASE
    #             WHEN COALESCE(SUM(t.estimated_cost), 0) > 0
    #             THEN ROUND((p.actual_revenue - COALESCE(SUM(t.estimated_cost), 0)) / SUM(t.estimated_cost), 2)
    #             ELSE 0
    #         END as roi_ratio
    #     FROM promotions p
    #     JOIN skus s ON p.sku_id = s.id
    #     LEFT JOIN token_usage t ON p.id = t.promotion_id
    #     WHERE p.status IN ('completed', 'retracted')
    #     GROUP BY p.id, p.promotion_code, s.name, p.actual_revenue
    #     ORDER BY roi_ratio DESC
    #     LIMIT 15
    # """)
    # roi_data = cursor.fetchall()

    # if roi_data:
    #     df = pd.DataFrame(roi_data, columns=["Code", "SKU", "Revenue", "Agent Cost", "Net Revenue", "ROI Ratio"])
    #     st.dataframe(df, use_container_width=True)

    #     # ROI Chart
    #     fig = px.bar(df, x="Code", y="ROI Ratio", title="Promotion ROI (Revenue/Cost Ratio)")
    #     st.plotly_chart(fig, use_container_width=True)
    # else:
    #     st.info("No ROI data available yet")

    # cursor.close()
    # conn.close()

except Exception as e:
    st.error(f"Error: {e}")
