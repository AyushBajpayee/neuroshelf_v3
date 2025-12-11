"""
Market Analysis Agent
Analyzes market conditions and identifies opportunities
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import config
from token_tracker import token_tracker
from mcp_client import mcp_client


def analyze_market_node(state: dict) -> dict:
    """Analyze market conditions and decide if action is needed"""
    print(f"  [Market Analyzer] Analyzing market conditions...")

    try:
        # Prepare context
        inventory = state.get("inventory_data", {})
        weather = state.get("weather_data", {})
        competitors = state.get("competitor_data", [])
        social = state.get("social_data", {})
        sell_through = state.get("sell_through_rate", {})

        # Create analysis prompt
        analysis_prompt = f"""
Analyze the following market data and determine if we should take action (create a promotion):

**Inventory Status:**
- Current Stock: {inventory.get('quantity', 0)} units
- Stock Status: {inventory.get('stock_status', 'unknown')}
- 7-Day Sell-Through: {sell_through.get('avg_daily_sales', 0)} units/day

**Weather Conditions:**
- Temperature: {weather.get('temperature_celsius', 0)}°C
- Condition: {weather.get('condition', 'unknown')}
- Extreme Weather: {weather.get('is_extreme', False)}

**Competitor Pricing:**
{format_competitors(competitors)}

**Social Trends:**
- Has Buzz: {social.get('has_buzz', False)}
- Sentiment Score: {social.get('overall_sentiment', 50)}/100
- Trending Topics: {social.get('trending_topics', [])}

**Decision Criteria:**
1. Excess inventory (>80% capacity) + demand opportunity = CREATE PROMOTION
2. Low sell-through + favorable conditions = CREATE PROMOTION
3. Competitor promotion + we're overpriced = CREATE PROMOTION
4. Otherwise = NO ACTION

Respond with JSON:
{{
    "should_act": true/false,
    "reasoning": "explanation",
    "opportunity_score": 0-100,
    "key_factors": ["factor1", "factor2"]
}}
"""

        # Call LLM
        llm = ChatOpenAI(
            model=config.OPENAI_CONFIG["model"],
            api_key=config.OPENAI_CONFIG["api_key"],
        )

        messages = [
            SystemMessage(content="You are an expert market analyst for retail pricing. Analyze data and make decisions."),
            HumanMessage(content=analysis_prompt),
        ]

        response = llm.invoke(messages)

        # Log token usage
        token_tracker.extract_and_log(
            response,
            agent_name="Market Analysis Agent",
            operation="analyze_market_conditions",
            sku_id=state["sku_id"],
            context={"store_id": state["store_id"]},
        )

        # Parse response (simplified - in production use JSON parsing)
        should_act = "true" in response.content.lower() and "should_act" in response.content.lower()

        state["should_act"] = should_act
        state["analysis_result"] = {
            "reasoning": response.content,
            "should_act": should_act,
        }

        # Log decision
        mcp_client.call_tool(
            "postgres",
            "log_agent_decision",
            {
                "agent_name": "Market Analysis Agent",
                "sku_id": state["sku_id"],
                "store_id": state["store_id"],
                "decision_type": "market_analysis",
                "reasoning": response.content[:500],
                "data_used": {
                    "inventory_status": inventory.get("stock_status"),
                    "temperature": weather.get("temperature_celsius"),
                    "competitor_count": len(competitors),
                },
                "decision_outcome": "act" if should_act else "no_action",
            },
        )

        print(f"  [Market Analyzer] Decision: {'ACT' if should_act else 'NO ACTION'}")

        return state

    except Exception as e:
        print(f"  [Market Analyzer] Error: {e}")
        state["error"] = str(e)
        state["should_act"] = False
        return state


def format_competitors(competitors):
    """Format competitor data for prompt"""
    if not competitors:
        return "No competitor data available"

    lines = []
    for comp in competitors[:3]:  # Top 3
        lines.append(
            f"- {comp.get('competitor_name')}: ${comp.get('price', 0):.2f} "
            f"({'PROMO' if comp.get('promotion') else 'Regular'})"
        )
    return "\n".join(lines)
