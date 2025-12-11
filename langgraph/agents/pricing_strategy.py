"""
Pricing Strategy Agent
Calculates optimal pricing strategy
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import config
from token_tracker import token_tracker


def design_pricing_node(state: dict) -> dict:
    """Design optimal pricing strategy"""
    print(f"  [Pricing Strategy] Designing pricing strategy...")

    try:
        inventory = state.get("inventory_data", {})
        competitors = state.get("competitor_data", [])
        analysis = state.get("analysis_result", {})

        # Get base price and cost
        base_price = inventory.get("base_price", 5.99)
        base_cost = inventory.get("base_cost", 3.50)

        # Find lowest competitor price
        lowest_comp_price = min([c.get("price", 999) for c in competitors]) if competitors else base_price

        prompt = f"""
Design an optimal pricing strategy:

**Current Situation:**
- Our Base Price: ${base_price:.2f}
- Our Cost: ${base_cost:.2f}
- Lowest Competitor: ${lowest_comp_price:.2f}
- Min Margin Required: {config.AGENT_CONFIG['min_margin_percent']}%
- Max Discount Allowed: {config.AGENT_CONFIG['max_discount_percent']}%

**Market Analysis:**
{analysis.get('reasoning', 'Action recommended')}

Calculate the optimal promotional price that:
1. Maintains minimum margin of {config.AGENT_CONFIG['min_margin_percent']}%
2. Is competitive with market
3. Maximizes both volume and profit

Respond with JSON:
{{
    "promotional_price": 0.00,
    "discount_percent": 0,
    "expected_margin": 0,
    "reasoning": "explanation"
}}
"""

        llm = ChatOpenAI(
            model=config.OPENAI_CONFIG["model"],
            api_key=config.OPENAI_CONFIG["api_key"],
        )

        response = llm.invoke([
            SystemMessage(content="You are a pricing strategy expert. Calculate optimal prices with margin safety."),
            HumanMessage(content=prompt),
        ])

        token_tracker.extract_and_log(
            response,
            agent_name="Pricing Strategy Agent",
            operation="calculate_optimal_price",
            sku_id=state["sku_id"],
        )

        # Simple parsing (in production, use robust JSON parsing)
        # For demo, calculate reasonable price
        target_price = lowest_comp_price * 0.95  # Slightly undercut competitor
        margin = ((target_price - base_cost) / target_price) * 100

        # Ensure minimum margin
        if margin < config.AGENT_CONFIG["min_margin_percent"]:
            target_price = base_cost / (1 - config.AGENT_CONFIG["min_margin_percent"] / 100)
            margin = config.AGENT_CONFIG["min_margin_percent"]

        discount_pct = ((base_price - target_price) / base_price) * 100

        state["pricing_strategy"] = {
            "original_price": base_price,
            "promotional_price": round(target_price, 2),
            "discount_percent": round(discount_pct, 1),
            "margin_percent": round(margin, 2),
            "reasoning": response.content[:300],
        }

        print(f"  [Pricing Strategy] Price: ${target_price:.2f} (Margin: {margin:.1f}%)")

        return state

    except Exception as e:
        print(f"  [Pricing Strategy] Error: {e}")
        state["error"] = str(e)
        return state
