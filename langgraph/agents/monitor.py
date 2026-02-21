"""
Monitoring Agent
Tracks promotion performance and retracts if necessary
"""

from mcp_client import mcp_client
import config
from runtime_tracker import set_current_agent


def monitor_performance_node(state: dict) -> dict:
    """Monitor promotion performance"""
    set_current_agent(
        "Monitoring Agent",
        sku_id=state.get("sku_id"),
        store_id=state.get("store_id"),
        promotion_id=state.get("promotion_id"),
    )
    promotion_id = state.get("promotion_id")

    if not promotion_id:
        return state

    try:
        # In a real implementation, this would:
        # 1. Query recent sales for this promotion
        # 2. Compare actual vs expected performance
        # 3. Check margin maintenance
        # 4. Decide if retraction is needed

        # For demo purposes, simulate monitoring logic
        # Actual implementation would query sales_transactions table

        # Log performance check
        mcp_client.call_tool(
            "postgres",
            "log_performance_metric",
            {
                "promotion_id": promotion_id,
                "units_sold_so_far": 0,  # Would be actual count
                "revenue_so_far": 0.0,
                "performance_ratio": 0.0,
                "is_profitable": True,
                "margin_maintained": True,
                "notes": "Monitoring check performed",
            },
        )

        # Decision logic (simplified)
        should_retract = False  # In reality, based on performance data

        state["should_retract"] = should_retract

        return state

    except Exception as e:
        print(f"  [Monitor] Error: {e}")
        return state


def retract_promotion_node(state: dict) -> dict:
    """Retract underperforming promotion"""
    set_current_agent(
        "Monitoring Agent (Retraction)",
        sku_id=state.get("sku_id"),
        store_id=state.get("store_id"),
        promotion_id=state.get("promotion_id"),
    )
    promotion_id = state.get("promotion_id")

    try:
        result = mcp_client.call_tool(
            "postgres",
            "retract_promotion",
            {
                "promotion_id": promotion_id,
                "reason": "Performance below threshold or margin compromised",
            },
        )

        print(f"  [Monitor] Promotion {promotion_id} RETRACTED")

        # Log decision
        mcp_client.call_tool(
            "postgres",
            "log_agent_decision",
            {
                "agent_name": "Monitoring Agent",
                "sku_id": state.get("sku_id"),
                "store_id": state.get("store_id"),
                "decision_type": "retract_promotion",
                "prompt_fed": None,
                "reasoning": "Performance monitoring triggered retraction",
                "data_used": state.get("performance_data", {}),
                "decision_outcome": "retracted",
                "promotion_id": promotion_id,
            },
        )

        return state

    except Exception as e:
        print(f"  [Monitor] Error retracting: {e}")
        return state
