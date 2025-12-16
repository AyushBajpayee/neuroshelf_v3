"""
Data Collection Agent
Gathers all necessary data for pricing decisions
"""

from langchain_core.messages import HumanMessage
from mcp_client import mcp_client
from token_tracker import token_tracker


def collect_data_node(state: dict) -> dict:
    """Collect data from all sources"""
    sku_id = state["sku_id"]
    store_id = state["store_id"]

    print(f"  [Data Collector] Gathering data for SKU {sku_id} at Store {store_id}...")

    try:
        # Collect inventory data
        inventory = mcp_client.call_tool(
            "postgres",
            "query_inventory_levels",
            {"sku_id": sku_id, "store_id": store_id},
        )

        # Collect sell-through rate
        sell_through = mcp_client.call_tool(
            "postgres",
            "calculate_sell_through_rate",
            {"sku_id": sku_id, "store_id": store_id, "days": 7},
        )

        # Collect weather data
        weather = mcp_client.call_tool(
            "weather", "get_current_weather", {"location_id": store_id}
        )

        # Collect competitor prices
        competitor = mcp_client.call_tool(
            "competitor", "get_competitor_prices", {"sku_id": sku_id, "location_id": store_id}
        )

        # Collect social trends
        if inventory and len(inventory) > 0:
            category = inventory[0].get("category", "food")
            social = mcp_client.call_tool(
                "social", "check_sku_sentiment", {"sku_category": category}
            )
        else:
            social = {}

        # Update state
        state["inventory_data"] = inventory[0] if inventory else {}
        state["weather_data"] = weather
        state["competitor_data"] = competitor
        state["social_data"] = social
        state["sell_through_rate"] = sell_through

        state["messages"].append(
            HumanMessage(content=f"Data collected successfully for SKU {sku_id} at Store {store_id}")
        )

        # Log minimal token usage for data collection (no LLM call here)
        # In real implementation, if LLM is used for data parsing, log accordingly
        print('Passing State from Data Collector Agent to next ->', state)
        return state

    except Exception as e:
        print(f"  [Data Collector] Error: {e}")
        state["error"] = str(e)
        print('Passing State from Data Collector Agent to next ->', state)
        return state
