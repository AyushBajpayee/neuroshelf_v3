"""
Execution Agent
Deploys promotions to the system
"""

from mcp_client import mcp_client
import config


def execute_promotion_node(state: dict) -> dict:
    """Execute and deploy promotion"""
    print(f"  [Executor] Deploying promotion...")

    try:
        promo_design = state.get("promotion_design", {})

        # Check if manual approval required
        if config.AGENT_CONFIG["require_manual_approval"]:
            print(f"  [Executor] Manual approval required - saving to pending_promotions")

            # Save to pending_promotions table
            pending_result = mcp_client.call_tool(
                "postgres",
                "create_pending_promotion",
                {
                    "sku_id": state["sku_id"],
                    "store_id": state["store_id"],
                    "promotion_type": promo_design["promotion_type"],
                    "discount_type": promo_design["discount_type"],
                    "discount_value": promo_design["discount_value"],
                    "original_price": promo_design["original_price"],
                    "promotional_price": promo_design["promotional_price"],
                    "margin_percent": promo_design["margin_percent"],
                    "proposed_valid_from": promo_design["valid_from"],
                    "proposed_valid_until": promo_design["valid_until"],
                    "target_radius_km": promo_design.get("target_radius_km"),
                    "expected_units_sold": promo_design.get("expected_units_sold"),
                    "expected_revenue": promo_design.get("expected_revenue"),
                    "agent_reasoning": promo_design.get("reason", "Agent recommends this promotion"),
                    "market_data": {
                        "inventory": state.get("inventory_data", {}),
                        "weather": state.get("weather_data", {}),
                        "competitors": state.get("competitor_data", []),
                        "social": state.get("social_data", {}),
                    },
                },
            )

            if not pending_result:
                raise Exception("Failed to create pending promotion - MCP call returned None")

            print(f"  [Executor] Promotion saved to pending_promotions (ID: {pending_result.get('id')})")

            state["execution_result"] = {
                "status": "pending_approval",
                "message": "Promotion requires manual approval",
                "pending_promotion_id": pending_result.get("id"),
            }

            # Log decision as pending
            mcp_client.call_tool(
                "postgres",
                "log_agent_decision",
                {
                    "agent_name": "Execution Agent",
                    "sku_id": state["sku_id"],
                    "store_id": state["store_id"],
                    "decision_type": "create_promotion",
                    "reasoning": promo_design.get("reason", "Promotion pending approval")[:500],
                    "data_used": promo_design,
                    "decision_outcome": "pending_approval",
                },
            )

            return state

        # Create promotion in database
        result = mcp_client.call_tool(
            "postgres",
            "create_promotion",
            {
                "sku_id": state["sku_id"],
                "store_id": state["store_id"],
                "promotion_type": promo_design["promotion_type"],
                "discount_type": promo_design["discount_type"],
                "discount_value": promo_design["discount_value"],
                "original_price": promo_design["original_price"],
                "promotional_price": promo_design["promotional_price"],
                "margin_percent": promo_design["margin_percent"],
                "valid_from": promo_design["valid_from"],
                "valid_until": promo_design["valid_until"],
                "target_radius_km": promo_design.get("target_radius_km"),
                "expected_units_sold": promo_design.get("expected_units_sold"),
                "expected_revenue": promo_design.get("expected_revenue"),
                "reason": promo_design.get("reason"),
            },
        )

        state["promotion_id"] = result.get("id")
        state["execution_result"] = {
            "status": "active",
            "promotion_code": result.get("promotion_code"),
            "promotion_id": result.get("id"),
        }

        # Log decision
        mcp_client.call_tool(
            "postgres",
            "log_agent_decision",
            {
                "agent_name": "Execution Agent",
                "sku_id": state["sku_id"],
                "store_id": state["store_id"],
                "decision_type": "create_promotion",
                "reasoning": promo_design.get("reason", "Promotion executed")[:500],
                "data_used": promo_design,
                "decision_outcome": "executed",
                "promotion_id": result.get("id"),
            },
        )

        print(f"  [Executor] Promotion {result.get('promotion_code')} ACTIVE")

        return state

    except Exception as e:
        print(f"  [Executor] Error: {e}")
        state["error"] = str(e)
        return state
