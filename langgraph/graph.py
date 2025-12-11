"""
LangGraph State Graph Definition
Defines the agent workflow and state transitions
"""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
import operator


# Define the state structure
class AgentState(TypedDict):
    """State passed between agents"""
    sku_id: int
    store_id: int
    messages: Annotated[Sequence[BaseMessage], operator.add]
    inventory_data: dict
    weather_data: dict
    competitor_data: dict
    social_data: dict
    sell_through_rate: dict
    analysis_result: dict
    pricing_strategy: dict
    promotion_design: dict
    execution_result: dict
    should_act: bool
    promotion_id: int
    performance_data: dict
    should_retract: bool
    error: str


def create_pricing_graph():
    """Create the LangGraph state graph"""
    workflow = StateGraph(AgentState)

    # Import agent functions (these will be in separate files)
    from agents.data_collector import collect_data_node
    from agents.market_analyzer import analyze_market_node
    from agents.pricing_strategy import design_pricing_node
    from agents.promo_designer import design_promotion_node
    from agents.executor import execute_promotion_node

    # Add nodes
    workflow.add_node("collect_data", collect_data_node)
    workflow.add_node("analyze_market", analyze_market_node)
    workflow.add_node("design_pricing", design_pricing_node)
    workflow.add_node("design_promotion", design_promotion_node)
    workflow.add_node("execute_promotion", execute_promotion_node)

    # Define conditional edges
    def should_act_decision(state: AgentState) -> str:
        """Decide if we should act on the analysis"""
        if state.get("should_act", False):
            return "design_pricing"
        return END

    def should_retract_decision(state: AgentState) -> str:
        """Decide if we should retract promotion"""
        if state.get("should_retract", False):
            return "retract"
        return "continue_monitoring"

    # Set entry point
    workflow.set_entry_point("collect_data")

    # Add edges
    workflow.add_edge("collect_data", "analyze_market")
    workflow.add_conditional_edges(
        "analyze_market",
        should_act_decision,
        {"design_pricing": "design_pricing", END: END},
    )
    workflow.add_edge("design_pricing", "design_promotion")
    workflow.add_edge("design_promotion", "execute_promotion")
    workflow.add_edge("execute_promotion", END)

    # Compile the graph
    app = workflow.compile()
    return app


# For monitoring active promotions
def create_monitoring_graph():
    """Create a separate graph for monitoring active promotions"""
    workflow = StateGraph(AgentState)

    from agents.monitor import monitor_performance_node, retract_promotion_node

    workflow.add_node("monitor", monitor_performance_node)
    workflow.add_node("retract", retract_promotion_node)

    workflow.set_entry_point("monitor")

    def should_retract(state: AgentState) -> str:
        if state.get("should_retract", False):
            return "retract"
        return END

    workflow.add_conditional_edges(
        "monitor", should_retract, {"retract": "retract", END: END}
    )
    workflow.add_edge("retract", END)

    app = workflow.compile()
    return app
