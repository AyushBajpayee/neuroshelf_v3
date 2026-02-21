"""
Decision Learning Agent
Loads or generates decision priors from historical behavior.
"""

import config
from mcp_client import mcp_client
from runtime_tracker import set_current_agent
from services.decision_learning_service import DecisionLearningService


decision_learning_service = DecisionLearningService(mcp_client)


def enrich_with_decision_priors_node(state: dict) -> dict:
    """Inject reusable decision priors into graph state."""
    set_current_agent(
        "Decision Learning Agent",
        sku_id=state.get("sku_id"),
        store_id=state.get("store_id"),
    )

    if not config.FEATURE_FLAGS["enable_decision_learning"]:
        state["decision_priors"] = {}
        return state

    print("  [Decision Learning] Loading behavioral priors...")

    try:
        priors = decision_learning_service.get_decision_priors(state) or {}
        state["decision_priors"] = priors

        mcp_client.call_tool(
            "postgres",
            "log_agent_decision",
            {
                "agent_name": "Decision Learning Agent",
                "sku_id": state["sku_id"],
                "store_id": state["store_id"],
                "decision_type": "decision_priors",
                "prompt_fed": None,
                "reasoning": (
                    "Loaded decision priors from behavioral memory."
                    if priors else "No priors available; fallback to baseline strategy."
                ),
                "data_used": {
                    "priors_available": bool(priors),
                    "prior_source": priors.get("source") if priors else "none",
                    "risk_flags": priors.get("risk_flags", []) if priors else [],
                },
                "decision_outcome": "priors_loaded" if priors else "fallback_no_priors",
            },
        )

    except Exception as exc:
        print(f"  [Decision Learning] Error: {exc}")
        state["decision_priors"] = {}

    return state

