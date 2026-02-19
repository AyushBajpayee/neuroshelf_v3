"""
Promotion Design Agent
Designs targeted promotional campaigns
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime, timedelta
import config
from mcp_client import mcp_client
from runtime_tracker import set_current_agent


def design_promotion_node(state: dict) -> dict:
    """Design promotion details"""
    set_current_agent(
        "Promotion Design Agent",
        sku_id=state.get("sku_id"),
        store_id=state.get("store_id"),
    )
    print(f"  [Promo Designer] Designing promotion...")

    try:
        pricing = state.get("pricing_strategy", {})
        weather = state.get("weather_data", {})
        social = state.get("social_data", {})

        # Determine promotion type based on conditions
        is_extreme_weather = weather.get("is_extreme", False)
        has_social_buzz = social.get("has_buzz", False)

        if is_extreme_weather or has_social_buzz:
            promo_type = "flash_sale"
            duration_hours = config.PROMOTION_DEFAULTS["flash_sale_duration_hours"]
        else:
            promo_type = "discount"
            duration_hours = config.PROMOTION_DEFAULTS["discount_duration_hours"]

        valid_from = datetime.now()
        valid_until = valid_from + timedelta(hours=duration_hours)

        # Estimate expected sales
        current_avg_daily = float(state.get("sell_through_rate", {}).get("avg_daily_sales", 10))
        promotion_multiplier = 2.5 if promo_type == "flash_sale" else 1.5
        expected_units = int(current_avg_daily * promotion_multiplier * (duration_hours / 24))

        promo_price = float(pricing.get("promotional_price", 5.99))
        expected_revenue = expected_units * promo_price

        state["promotion_design"] = {
            "promotion_type": promo_type,
            "discount_type": "percentage",
            "discount_value": pricing.get("discount_percent", 20),
            "original_price": pricing.get("original_price", 6.99),
            "promotional_price": promo_price,
            "margin_percent": pricing.get("margin_percent", 15),
            "valid_from": valid_from.isoformat(),
            "valid_until": valid_until.isoformat(),
            "target_radius_km": config.PROMOTION_DEFAULTS["target_radius_km"],
            "expected_units_sold": expected_units,
            "expected_revenue": round(expected_revenue, 2),
            "reason": f"{promo_type.upper()}: {pricing.get('reasoning', 'Market opportunity detected')}",
        }

        print(f"  [Promo Designer] {promo_type.upper()} for {duration_hours}h, expect {expected_units} units")
        # print('Passing State from Promo Designer Agent to next ->', state)
        # Log decision
        mcp_client.call_tool(
            "postgres",
            "log_agent_decision",
            {
                "agent_name": "Promotion Design Agent",
                "sku_id": state["sku_id"],
                "store_id": state["store_id"],
                "decision_type": "promotion_design",
                "prompt_fed": None,
                "reasoning": 'Promotion designed based on pricing strategy',
                "data_used": {
                    "pricing_strategy": pricing,
                    "weather_data": weather,
                    "social_data": social,
                },
                "decision_outcome": "no_action",
            },
        )
        return state

    except Exception as e:
        print(f"  [Promo Designer] Error: {e}")
        state["error"] = str(e)
        # print('Passing State from Promo Designer Agent to next ->', state)
        return state
