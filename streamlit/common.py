"""
Shared Streamlit utilities:
- database connection
- agent control/status sidebar
"""

import os
from typing import Optional, Tuple

import httpx
import psycopg2
import streamlit as st

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "pricing_user"),
    "password": os.getenv("DB_PASSWORD", "pricing_pass"),
    "database": os.getenv("DB_NAME", "pricing_intelligence"),
}

LANGGRAPH_API_URL = os.getenv("LANGGRAPH_API_URL", "http://langgraph-core:8000")


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def get_agent_status() -> Tuple[Optional[dict], Optional[str]]:
    """Get agent runtime status from langgraph-core."""
    try:
        response = httpx.get(f"{LANGGRAPH_API_URL}/status", timeout=5.0)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)


def set_agent_running(should_run: bool) -> Tuple[bool, str]:
    """Start or stop the autonomous agent loop."""
    endpoint = "start" if should_run else "stop"
    try:
        response = httpx.post(f"{LANGGRAPH_API_URL}/agent/{endpoint}", timeout=10.0)
        response.raise_for_status()
        payload = response.json()
        return payload.get("success", False), payload.get("message", "No message returned")
    except Exception as e:
        return False, str(e)


def render_agent_control(agent_status: Optional[dict], status_error: Optional[str], key_prefix: str = "global"):
    """Render start/stop controls in sidebar."""
    header_col, refresh_col = st.columns([5, 1])
    with header_col:
        st.subheader("Agent Control")
    with refresh_col:
        if st.button("↻", key=f"{key_prefix}_agent_refresh", help="Refresh current agent state"):
            st.rerun()

    if status_error:
        st.warning("Agent control unavailable")
        st.caption(status_error)
        return

    if not agent_status:
        st.warning("Agent status unavailable")
        return

    running = agent_status.get("running", False)
    cycle_progress = agent_status.get("next_target_index", 0)
    cycle_total = agent_status.get("targets_in_cycle", 0)
    next_target = agent_status.get("next_target_after_current", agent_status.get("next_target"))
    has_next_after_current = "next_target_after_current" in agent_status
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
        st.caption(f"Next Target: SKU {next_target.get('sku_id')} @ Store {next_target.get('store_id')}")
    elif running and has_next_after_current:
        st.caption("Next Target: None (end of cycle / monitoring)")

    if running:
        if st.button("Stop Agents", key=f"{key_prefix}_agent_stop", use_container_width=True):
            success, message = set_agent_running(False)
            if success:
                st.warning(message)
            else:
                st.error(message)
            st.rerun()
    else:
        if st.button("Start Agents", key=f"{key_prefix}_agent_start", type="primary", use_container_width=True):
            success, message = set_agent_running(True)
            if success:
                st.success(message)
            else:
                st.error(message)
            st.rerun()


def render_sidebar(show_navigation: bool = False, key_prefix: str = "global"):
    """Render shared sidebar content. Agent Control is always present."""
    agent_status, status_error = get_agent_status()

    with st.sidebar:
        if show_navigation:
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

        render_agent_control(agent_status, status_error, key_prefix=key_prefix)

    return agent_status, status_error
