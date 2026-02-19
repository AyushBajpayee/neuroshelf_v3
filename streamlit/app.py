"""
Pricing Intelligence Agent - Streamlit Dashboard
Main application entry point
"""

import os

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Pricing Intelligence Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "pricing_user"),
    "password": os.getenv("DB_PASSWORD", "pricing_pass"),
    "database": os.getenv("DB_NAME", "pricing_intelligence"),
}

LANGGRAPH_API_URL = os.getenv("LANGGRAPH_API_URL", "http://langgraph-core:8000")


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)


def get_agent_status():
    """Get agent runtime status from langgraph-core."""
    try:
        response = httpx.get(f"{LANGGRAPH_API_URL}/status", timeout=5.0)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


def set_agent_running(should_run: bool):
    """Start or stop the autonomous agent loop."""
    endpoint = "start" if should_run else "stop"
    try:
        response = httpx.post(f"{LANGGRAPH_API_URL}/agent/{endpoint}", timeout=10.0)
        response.raise_for_status()
        payload = response.json()
        return payload.get("success", False), payload.get("message", "No message returned")
    except Exception as e:
        return False, str(e)


def render_agent_control(agent_status, status_error):
    """Render start/stop controls in sidebar."""
    st.subheader("Agent Control")

    if status_error:
        st.warning("Agent control unavailable")
        st.caption(status_error)
        return

    running = agent_status.get("running", False)
    cycle_progress = agent_status.get("next_target_index", 0)
    cycle_total = agent_status.get("targets_in_cycle", 0)
    next_target = agent_status.get("next_target")
    in_progress_target = agent_status.get("in_progress_target")
    current_agent = agent_status.get("current_agent")
    current_sku = agent_status.get("current_sku_id")
    current_store = agent_status.get("current_store_id")

    state_label = "Running" if running else "Paused"
    st.caption(f"State: {state_label}")
    st.caption(f"Progress: {cycle_progress}/{cycle_total}")
    st.caption(f"Completed Cycles: {agent_status.get('cycles_completed', 0)}")

    if in_progress_target:
        st.caption(
            f"In Progress: SKU {in_progress_target.get('sku_id')} @ Store {in_progress_target.get('store_id')}"
        )
    elif current_sku and current_store:
        st.caption(f"In Progress: SKU {current_sku} @ Store {current_store}")
    else:
        st.caption("In Progress: None")

    st.caption(f"Current Agent: {current_agent or 'Idle'}")

    if next_target:
        st.caption(
            f"Next Target: SKU {next_target.get('sku_id')} @ Store {next_target.get('store_id')}"
        )

    if running:
        if st.button("Stop Agents", use_container_width=True):
            success, message = set_agent_running(False)
            if success:
                st.warning(message)
            else:
                st.error(message)
            st.rerun()
    else:
        if st.button("Start Agents", type="primary", use_container_width=True):
            success, message = set_agent_running(True)
            if success:
                st.success(message)
            else:
                st.error(message)
            st.rerun()


def main():
    """Main dashboard page"""
    agent_status, status_error = get_agent_status()

    st.title("🤖 Pricing Intelligence & Promotion Agent")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        st.info(
            """
            **Welcome to the Pricing Intelligence Dashboard**

            Use the pages above to:
            - Monitor SKU performance
            - View active promotions
            - Approve pending promotions
            - Track costs and ROI
            - Control simulators
            - Analyze agent decisions
            """
        )
        render_agent_control(agent_status, status_error)

    # Main dashboard content
    col1, col2, col3, col4, col5 = st.columns(5)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get metrics
        cursor.execute("SELECT COUNT(*) as count FROM skus WHERE is_active = true")
        sku_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM promotions WHERE status = 'active'")
        active_promos = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM pending_promotions WHERE status = 'pending'")
        pending_promos = cursor.fetchone()["count"]

        cursor.execute("SELECT SUM(actual_revenue) as revenue FROM promotions WHERE status IN ('active', 'completed')")
        total_revenue = cursor.fetchone()["revenue"] or 0

        cursor.execute("SELECT SUM(estimated_cost) as cost FROM token_usage WHERE timestamp >= NOW() - INTERVAL '24 hours'")
        daily_cost = cursor.fetchone()["cost"] or 0

        # Display metrics
        with col1:
            st.metric("Active SKUs", sku_count)

        with col2:
            st.metric("Active Promotions", active_promos)

        with col3:
            st.metric("Pending Approval", pending_promos, delta=None if pending_promos == 0 else "Action Required")

        with col4:
            st.metric("Total Revenue", f"${total_revenue:,.2f}")

        with col5:
            st.metric("24h Agent Cost", f"${daily_cost:.4f}")

        st.markdown("---")

        # Recent promotions
        st.subheader("Recent Promotions")
        cursor.execute(
            """
            SELECT
                p.promotion_code,
                s.name as sku_name,
                st.name as store_name,
                p.promotional_price,
                p.discount_value,
                p.status,
                p.created_at,
                p.actual_units_sold,
                p.expected_units_sold
            FROM promotions p
            JOIN skus s ON p.sku_id = s.id
            JOIN stores st ON p.store_id = st.id
            ORDER BY p.created_at DESC
            LIMIT 10
            """
        )
        recent_promos = cursor.fetchall()

        if recent_promos:
            import pandas as pd

            df = pd.DataFrame(recent_promos)
            df["performance"] = (df["actual_units_sold"] / df["expected_units_sold"] * 100).round(1)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No promotions yet. Agent is analyzing market conditions...")

        st.markdown("---")

        # Quick stats
        stats_col1, stats_col2 = st.columns(2)

        with stats_col1:
            st.subheader("Top Performing SKUs")
            cursor.execute(
                """
                SELECT
                    s.name,
                    COUNT(p.id) as promo_count,
                    SUM(p.actual_revenue) as revenue
                FROM skus s
                LEFT JOIN promotions p ON s.id = p.sku_id AND p.status = 'completed'
                GROUP BY s.id, s.name
                ORDER BY revenue DESC NULLS LAST
                LIMIT 5
                """
            )
            top_skus = cursor.fetchall()

            if top_skus:
                for sku in top_skus:
                    st.write(f"**{sku['name']}**: {sku['promo_count']} promos, ${sku['revenue'] or 0:.2f}")
            else:
                st.info("No data available yet")

        with stats_col2:
            st.subheader("Cost by Agent")
            cursor.execute(
                """
                SELECT
                    agent_name,
                    SUM(estimated_cost) as cost,
                    COUNT(*) as operations
                FROM token_usage
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY agent_name
                ORDER BY cost DESC
                LIMIT 5
                """
            )
            agent_costs = cursor.fetchall()

            if agent_costs:
                for agent in agent_costs:
                    st.write(f"**{agent['agent_name']}**: ${agent['cost']:.4f} ({agent['operations']} ops)")
            else:
                st.info("No cost data available yet")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Error connecting to database: {e}")

    # System status
    st.markdown("---")
    st.subheader("System Status")

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        st.write("**LangGraph Agent**")
        if status_error:
            st.warning("Unavailable")
        else:
            if agent_status.get("running"):
                st.success("Running")
            else:
                st.info("Paused")

    with status_col2:
        st.write("**MCP Servers**")
        all_healthy = True
        for server in ["postgres", "weather", "competitor", "social"]:
            try:
                port = {"postgres": 3000, "weather": 3001, "competitor": 3002, "social": 3003}[server]
                response = httpx.get(f"http://mcp-{server}:{port}/health", timeout=5.0)
                if response.status_code != 200:
                    all_healthy = False
            except Exception:
                all_healthy = False

        if all_healthy:
            st.success("All Healthy")
        else:
            st.warning("Some Unavailable")

    with status_col3:
        st.write("**Database**")
        try:
            conn = get_db_connection()
            conn.close()
            st.success("Connected")
        except Exception:
            st.error("Disconnected")


if __name__ == "__main__":
    main()
