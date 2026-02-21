"""
Approval Queue Page
Manual approval interface for pending promotions
"""

import streamlit as st
import requests
import json
from datetime import datetime
import sys
sys.path.append('..')
from common import render_sidebar

render_sidebar(show_navigation=False, key_prefix="approval_queue")

st.title("✅ Promotion Approval Queue")
st.markdown("Review and approve/reject agent-recommended promotions")

# Configuration
MCP_POSTGRES_URL = "http://mcp-postgres:3000"


def call_mcp_tool(tool_name: str, parameters: dict):
    """Call MCP Postgres tool"""
    try:
        response = requests.post(
            f"{MCP_POSTGRES_URL}/tool",
            json={"tool_name": tool_name, "parameters": parameters},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("success"):
            return result.get("data")
        else:
            st.error(f"Tool error: {result.get('error')}")
            return None
    except Exception as e:
        st.error(f"Failed to call MCP tool: {str(e)}")
        return None


# Fetch pending promotions
st.subheader("Pending Promotions")

col1, col2 = st.columns([3, 1])
with col1:
    status_filter = st.selectbox(
        "Status Filter",
        options=["pending", "approved", "rejected"],
        index=0,
    )

with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Get pending promotions
pending_promotions = call_mcp_tool(
    "get_pending_promotions",
    {"status": status_filter}
)

if not pending_promotions:
    st.info(f"No {status_filter} promotions found.")
else:
    st.success(f"Found {len(pending_promotions)} {status_filter} promotion(s)")

    for idx, promo in enumerate(pending_promotions):
        with st.expander(
            f"🎯 {promo['sku_name']} @ {promo['store_name']} - "
            f"${float(promo['promotional_price']):.2f} (ID: {promo['id']})",
            expanded=(idx == 0 and status_filter == "pending")
        ):
            # Promotion Details
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**📦 Product Info**")
                st.write(f"**SKU:** {promo['sku_code']}")
                st.write(f"**Category:** {promo['category']}")
                st.write(f"**Store:** {promo['store_code']}")

            with col2:
                st.markdown("**💰 Pricing**")
                st.write(f"**Original Price:** ${float(promo['original_price']):.2f}")
                st.write(f"**Promo Price:** ${float(promo['promotional_price']):.2f}")
                st.write(f"**Discount:** {float(promo['discount_value']):.2f}%")
                st.write(f"**Margin:** {float(promo['margin_percent']):.2f}%")

            with col3:
                st.markdown("**📅 Timing**")
                st.write(f"**Type:** {promo['promotion_type']}")
                st.write(f"**Start:** {promo['proposed_valid_from']}")
                st.write(f"**End:** {promo['proposed_valid_until']}")
                st.write(f"**Created:** {promo['created_at']}")

            # Expected Performance
            st.markdown("**📊 Expected Performance**")
            perf_col1, perf_col2 = st.columns(2)
            with perf_col1:
                st.metric("Expected Units Sold", promo.get('expected_units_sold', 'N/A'))
            with perf_col2:
                st.metric("Expected Revenue", f"${float(promo.get('expected_revenue', 0)):.2f}" if promo.get('expected_revenue') else 'N/A')

            # Agent Reasoning
            st.markdown("**🤖 Agent Reasoning**")
            st.info(promo['agent_reasoning'])

            # Market Data (if available)
            if promo.get('market_data'):
                st.markdown("**📈 Market Data**")
                if st.checkbox("Show Market Data Details", key=f"market_data_{promo['id']}"):
                    try:
                        market_data = json.loads(promo['market_data']) if isinstance(promo['market_data'], str) else promo['market_data']
                        st.json(market_data)
                    except:
                        st.write(promo['market_data'])

            # Status and Review Info
            st.markdown("**📋 Status**")
            status_col1, status_col2, status_col3 = st.columns(3)
            with status_col1:
                status_color = {
                    "pending": "🟡",
                    "approved": "🟢",
                    "rejected": "🔴"
                }
                st.write(f"**Status:** {status_color.get(promo['status'], '⚪')} {promo['status'].upper()}")

            with status_col2:
                if promo.get('reviewed_by'):
                    st.write(f"**Reviewed By:** {promo['reviewed_by']}")

            with status_col3:
                if promo.get('reviewed_at'):
                    st.write(f"**Reviewed At:** {promo['reviewed_at']}")

            if promo.get('reviewer_notes'):
                st.markdown("**📝 Reviewer Notes**")
                st.write(promo['reviewer_notes'])

            # Approval Actions (only for pending promotions)
            if promo['status'] == 'pending':
                st.markdown("---")
                st.markdown("**✅ Approval Actions**")

                action_col1, action_col2 = st.columns(2)

                with action_col1:
                    with st.form(key=f"approve_form_{promo['id']}"):
                        st.markdown("**Approve Promotion**")
                        reviewed_by = st.text_input("Your Name", key=f"approve_name_{promo['id']}")
                        reviewer_notes = st.text_area("Notes (optional)", key=f"approve_notes_{promo['id']}")

                        if st.form_submit_button("✅ Approve", type="primary", use_container_width=True):
                            if not reviewed_by:
                                st.error("Please enter your name")
                            else:
                                result = call_mcp_tool(
                                    "approve_promotion",
                                    {
                                        "pending_promotion_id": promo['id'],
                                        "reviewed_by": reviewed_by,
                                        "reviewer_notes": reviewer_notes if reviewer_notes else None,
                                    }
                                )

                                if result:
                                    st.success(f"✅ Promotion approved! Created promotion {result['promotion_code']}")
                                    st.balloons()
                                    st.rerun()

                with action_col2:
                    with st.form(key=f"reject_form_{promo['id']}"):
                        st.markdown("**Reject Promotion**")
                        reviewed_by_reject = st.text_input("Your Name", key=f"reject_name_{promo['id']}")
                        rejection_reason = st.text_area("Rejection Reason (required)", key=f"reject_reason_{promo['id']}")

                        if st.form_submit_button("❌ Reject", type="secondary", use_container_width=True):
                            if not reviewed_by_reject:
                                st.error("Please enter your name")
                            elif not rejection_reason:
                                st.error("Please provide a rejection reason")
                            else:
                                result = call_mcp_tool(
                                    "reject_promotion",
                                    {
                                        "pending_promotion_id": promo['id'],
                                        "reviewed_by": reviewed_by_reject,
                                        "reviewer_notes": rejection_reason,
                                    }
                                )

                                if result:
                                    st.success("❌ Promotion rejected")
                                    st.rerun()

# Statistics
st.markdown("---")
st.subheader("📊 Approval Queue Statistics")

stats_col1, stats_col2, stats_col3 = st.columns(3)

# Get counts for all statuses
pending_count = len(call_mcp_tool("get_pending_promotions", {"status": "pending"}) or [])
approved_count = len(call_mcp_tool("get_pending_promotions", {"status": "approved"}) or [])
rejected_count = len(call_mcp_tool("get_pending_promotions", {"status": "rejected"}) or [])

with stats_col1:
    st.metric("🟡 Pending", pending_count)

with stats_col2:
    st.metric("🟢 Approved", approved_count)

with stats_col3:
    st.metric("🔴 Rejected", rejected_count)

# Total
total = pending_count + approved_count + rejected_count
if total > 0:
    approval_rate = (approved_count / total) * 100
    st.info(f"**Approval Rate:** {approval_rate:.1f}% ({approved_count}/{total})")
