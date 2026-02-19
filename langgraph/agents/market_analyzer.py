"""
Market Analysis Agent
Analyzes market conditions and identifies opportunities
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import config
from token_tracker import token_tracker
from mcp_client import mcp_client
import tiktoken
import json
from runtime_tracker import set_current_agent

def analyze_market_node(state: dict) -> dict:
    """Analyze market conditions and decide if action is needed"""
    set_current_agent(
        "Market Analysis Agent",
        sku_id=state.get("sku_id"),
        store_id=state.get("store_id"),
    )
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
        system_message = "You are an expert market analyst for retail pricing. Analyze data and make decisions."

        # Call LLM
        llm = ChatOpenAI(
            model=config.OPENAI_CONFIG["model"],
            api_key=config.OPENAI_CONFIG["api_key"],
            temperature=1.0,
        )

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=analysis_prompt),
        ]

        response = llm.invoke(messages)
        # print(f"  [Market Analyzer] LLM Response: {response}")
        # Log token usage
        encoding = tiktoken.get_encoding("cl100k_base")
        input_text = system_message + analysis_prompt
        output_text = response.content
        input_token = len(encoding.encode(input_text))
        output_token = len(encoding.encode(output_text))
        print(f"Input token count: {input_token}, Output token count: {output_token}")
        print('Logging token usage...')
        token_tracker.log_usage(
            agent_name="Market Analysis Agent",
            operation="analyze_market_conditions",
            prompt_tokens=input_token,
            completion_tokens=output_token,
            sku_id=state["sku_id"],
            context={"store_id": state["store_id"]}
        )
        print(f'Token usage logged for market analysis agent.')
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
                "prompt_fed": input_text,
                "reasoning": json.loads(response.content)['reasoning'],
                "data_used": {
                    "inventory_status": inventory.get("stock_status"),
                    "temperature": weather.get("temperature_celsius"),
                    "competitor_count": len(competitors),
                },
                "decision_outcome": "act" if should_act else "no_action",
            },
        )

        print(f"  [Market Analyzer] Decision: {'ACT' if should_act else 'NO ACTION'}")
        # print('Passing State from Market Analyzer Agent to next ->', state)
        return state

    except Exception as e:
        print(f"  [Market Analyzer] Error: {e}")
        state["error"] = str(e)
        state["should_act"] = False
        # print('Passing State from Market Analyzer Agent to next ->', state)
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
