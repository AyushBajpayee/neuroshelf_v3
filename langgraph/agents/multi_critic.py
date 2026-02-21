"""
Multi-Critic Review Agent
Runs internal evaluators and arbitrates approve/revise/reject.
"""

from typing import Any, Dict, List

import config
from mcp_client import mcp_client
from runtime_tracker import set_current_agent


def _profit_guardian(promotion: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    min_margin = config.AGENT_CONFIG["min_margin_percent"]
    margin = float(promotion.get("margin_percent", 0) or 0)
    expected_units = float(promotion.get("expected_units_sold", 0) or 0)
    promo_price = float(promotion.get("promotional_price", 0) or 0)
    base_cost = float(state.get("inventory_data", {}).get("base_cost", 0) or 0)
    expected_profit = (promo_price - base_cost) * expected_units

    score = max(0, min(100, (margin * 3.0) + (expected_profit * 0.05)))
    risks: List[str] = []

    if margin < min_margin:
        risks.append("margin_below_floor")
        recommendation = "reject"
    elif margin < min_margin + 2:
        risks.append("margin_near_floor")
        recommendation = "revise"
    else:
        recommendation = "approve"

    rationale = (
        f"Margin={margin:.2f}% vs floor={min_margin:.2f}%. "
        f"Expected profit={expected_profit:.2f}."
    )
    return {
        "evaluator": "Profit Guardian",
        "score": round(score, 3),
        "rationale": rationale,
        "risk_flags": risks,
        "recommendation": recommendation,
    }


def _growth_hacker(promotion: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    discount = float(promotion.get("discount_value", 0) or 0)
    expected_units = float(promotion.get("expected_units_sold", 0) or 0)
    baseline_units = float(state.get("sell_through_rate", {}).get("avg_daily_sales", 1) or 1)
    uplift = expected_units / max(baseline_units, 1.0)

    score = max(0, min(100, (uplift * 35.0) + (discount * 1.2)))
    risks: List[str] = []

    if uplift < 1.1:
        risks.append("limited_growth_uplift")
        recommendation = "revise"
    elif discount < 1 and uplift < 1.0:
        risks.append("low_stimulation")
        recommendation = "reject"
    else:
        recommendation = "approve"

    rationale = (
        f"Expected unit uplift={uplift:.2f}x baseline. "
        f"Discount={discount:.2f}%."
    )
    return {
        "evaluator": "Growth Hacker",
        "score": round(score, 3),
        "rationale": rationale,
        "risk_flags": risks,
        "recommendation": recommendation,
    }


def _brand_guardian(promotion: Dict[str, Any]) -> Dict[str, Any]:
    discount = float(promotion.get("discount_value", 0) or 0)
    promotion_type = str(promotion.get("promotion_type", "discount"))
    max_discount = float(config.AGENT_CONFIG["max_discount_percent"])

    fatigue_penalty = 12 if promotion_type == "flash_sale" else 0
    score = max(0, min(100, 100 - (discount * 2.0) - fatigue_penalty))

    risks: List[str] = []
    if discount >= max_discount:
        risks.append("max_discount_boundary")
    if discount > max_discount * 0.8:
        risks.append("brand_dilution_risk")

    if score < 40:
        recommendation = "reject"
    elif score < 60:
        recommendation = "revise"
    else:
        recommendation = "approve"

    rationale = (
        f"Discount={discount:.2f}% with promotion_type={promotion_type}. "
        f"Brand score penalized for discount intensity/frequency."
    )
    return {
        "evaluator": "Brand Guardian",
        "score": round(score, 3),
        "rationale": rationale,
        "risk_flags": risks,
        "recommendation": recommendation,
    }


def _arbitrate(evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not evaluations:
        return {
            "action": "approve",
            "reason": "No evaluator outputs available.",
            "average_score": 0.0,
        }

    avg_score = sum(float(e["score"]) for e in evaluations) / len(evaluations)
    has_reject = any(e["recommendation"] == "reject" for e in evaluations)
    has_revise = any(e["recommendation"] == "revise" for e in evaluations)

    if has_reject or avg_score < config.CRITIC_CONFIG["reject_threshold"]:
        action = "reject"
    elif has_revise or avg_score < config.CRITIC_CONFIG["revise_threshold"]:
        action = "revise"
    else:
        action = "approve"

    return {
        "action": action,
        "average_score": round(avg_score, 3),
        "reason": (
            f"Arbitration={action}. avg_score={avg_score:.2f}, "
            f"has_revise={has_revise}, has_reject={has_reject}"
        ),
    }


def _apply_revision_if_needed(promotion: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    if decision.get("action") != "revise":
        return promotion

    revised = dict(promotion)
    original_price = float(revised.get("original_price", 0) or 0)
    base_discount = float(revised.get("discount_value", 0) or 0)
    new_discount = max(0.0, min(base_discount - 2.0, config.AGENT_CONFIG["max_discount_percent"]))
    revised_price = round(original_price * (1 - new_discount / 100.0), 2) if original_price > 0 else revised.get("promotional_price")

    revised["discount_value"] = round(new_discount, 2)
    revised["discount_percent"] = round(new_discount, 2)
    revised["promotional_price"] = revised_price
    revised["reason"] = (
        f"{revised.get('reason', '')} | revised by multi-critic arbitration to reduce risk."
    ).strip()
    return revised


def multi_critic_review_node(state: dict) -> dict:
    """Evaluate proposal using Profit/Growth/Brand critics and arbitrate."""
    set_current_agent(
        "Multi-Critic Review Agent",
        sku_id=state.get("sku_id"),
        store_id=state.get("store_id"),
    )

    if not config.FEATURE_FLAGS["enable_multi_critic"]:
        state["critic_decision"] = {
            "enabled": False,
            "action": "approve",
            "reason": "Multi-critic disabled; bypassed.",
            "average_score": None,
        }
        state["critic_evaluations"] = []
        return state

    promotion = dict(state.get("promotion_design") or {})
    if not promotion:
        state["critic_decision"] = {
            "enabled": True,
            "action": "reject",
            "reason": "No promotion design available for review.",
            "average_score": 0.0,
        }
        state["critic_evaluations"] = []
        return state

    print("  [Multi-Critic] Evaluating proposal with Profit/Growth/Brand critics...")

    evaluations = [
        _profit_guardian(promotion, state),
        _growth_hacker(promotion, state),
        _brand_guardian(promotion),
    ]
    decision = _arbitrate(evaluations)
    decision["enabled"] = True
    state["critic_evaluations"] = evaluations
    state["critic_decision"] = decision

    if decision.get("action") == "revise":
        state["promotion_design"] = _apply_revision_if_needed(promotion, decision)

    for evaluation in evaluations:
        try:
            mcp_client.call_tool(
                "postgres",
                "log_evaluator_score",
                {
                    "sku_id": state.get("sku_id"),
                    "store_id": state.get("store_id"),
                    "evaluator_name": evaluation["evaluator"],
                    "score": evaluation["score"],
                    "rationale": evaluation["rationale"],
                    "risk_flags": {"flags": evaluation["risk_flags"]},
                    "recommendation": evaluation["recommendation"],
                    "arbitration_decision": decision.get("action"),
                },
            )
        except Exception as exc:
            print(f"  [Multi-Critic] Evaluator score logging failed: {exc}")

    try:
        mcp_client.call_tool(
            "postgres",
            "log_agent_decision",
            {
                "agent_name": "Multi-Critic Review Agent",
                "sku_id": state["sku_id"],
                "store_id": state["store_id"],
                "decision_type": "multi_critic_review",
                "prompt_fed": None,
                "reasoning": decision.get("reason", "Critic arbitration complete."),
                "data_used": {
                    "evaluations": evaluations,
                    "average_score": decision.get("average_score"),
                },
                "decision_outcome": decision.get("action"),
            },
        )
    except Exception as exc:
        print(f"  [Multi-Critic] Agent decision logging failed: {exc}")

    return state

