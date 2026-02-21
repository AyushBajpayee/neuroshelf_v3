"""
Offer Optimization Agent
Runs bounded iterative optimization on promotion proposals.
"""

from typing import Any, Dict, List

import config
from mcp_client import mcp_client
from runtime_tracker import set_current_agent


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _evaluate_offer(candidate: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    inventory = state.get("inventory_data", {})
    min_margin = config.AGENT_CONFIG["min_margin_percent"]
    max_discount = config.AGENT_CONFIG["max_discount_percent"]
    objective = config.AGENT_CONFIG["optimization_objective"]

    base_cost = float(inventory.get("base_cost", 0.01) or 0.01)
    promo_price = float(candidate.get("promotional_price", 0.01) or 0.01)
    discount_pct = float(candidate.get("discount_value", 0) or 0)

    margin_percent = ((promo_price - base_cost) / promo_price) * 100 if promo_price > 0 else 0

    baseline_units = int(candidate.get("expected_units_sold", 1) or 1)
    demand_multiplier = 1 + (discount_pct / 100.0) * 1.25
    expected_units = max(1, int(round(baseline_units * demand_multiplier)))
    expected_profit = (promo_price - base_cost) * expected_units
    expected_revenue = promo_price * expected_units

    constraints = {
        "margin_ok": margin_percent >= min_margin,
        "discount_ok": discount_pct <= max_discount,
        "non_negative_discount": discount_pct >= 0,
    }
    all_constraints_ok = all(constraints.values())

    if objective == "inventory_reduction":
        objective_score = (expected_units * 5) + (expected_profit * 0.1)
    elif objective == "revenue_lift":
        objective_score = expected_revenue
    elif objective == "sell_through_acceleration":
        objective_score = expected_units * (1 + discount_pct / 100.0)
    else:
        objective_score = expected_profit

    if not all_constraints_ok:
        objective_score -= 1_000_000

    return {
        "objective_name": objective,
        "objective_score": round(float(objective_score), 4),
        "constraints": constraints,
        "expected_units_sold": expected_units,
        "expected_revenue": round(float(expected_revenue), 2),
        "margin_percent": round(float(margin_percent), 2),
    }


def optimize_offer_node(state: dict) -> dict:
    """Iteratively optimize an offer while respecting hard constraints."""
    set_current_agent(
        "Offer Optimization Agent",
        sku_id=state.get("sku_id"),
        store_id=state.get("store_id"),
    )

    if not config.FEATURE_FLAGS["enable_optimization_loop"]:
        state["optimization_result"] = {
            "enabled": False,
            "iterations": 0,
            "selected_iteration": None,
            "note": "Optimization disabled; single-pass promotion design preserved.",
        }
        return state

    promotion = dict(state.get("promotion_design") or {})
    if not promotion:
        return state

    print("  [Offer Optimizer] Running bounded offer optimization loop...")

    max_iterations = max(1, min(config.AGENT_CONFIG["optimization_max_iterations"], 10))
    original_price = float(promotion.get("original_price", 0.01) or 0.01)
    base_discount = float(promotion.get("discount_value", 0) or 0)
    max_discount = float(config.AGENT_CONFIG["max_discount_percent"])
    deltas = [0, 2, -2, 4, -4, 6, -6, 8, -8, 10]

    iteration_logs: List[Dict[str, Any]] = []
    best_offer = dict(promotion)
    best_eval = _evaluate_offer(best_offer, state)
    best_iteration = 0

    for iteration_idx in range(max_iterations):
        delta = deltas[iteration_idx] if iteration_idx < len(deltas) else 0
        candidate_discount = _clamp(base_discount + delta, 0, max_discount)
        candidate_price = round(original_price * (1 - candidate_discount / 100.0), 2)

        candidate = dict(promotion)
        candidate["discount_value"] = round(candidate_discount, 2)
        candidate["promotional_price"] = candidate_price
        candidate["discount_percent"] = round(candidate_discount, 2)

        evaluation = _evaluate_offer(candidate, state)

        candidate["margin_percent"] = evaluation["margin_percent"]
        candidate["expected_units_sold"] = evaluation["expected_units_sold"]
        candidate["expected_revenue"] = evaluation["expected_revenue"]

        log_payload = {
            "iteration_index": iteration_idx,
            "objective_name": evaluation["objective_name"],
            "objective_score": evaluation["objective_score"],
            "candidate_offer": candidate,
            "constraints_checked": evaluation["constraints"],
            "sku_id": state.get("sku_id"),
            "store_id": state.get("store_id"),
            "is_selected": False,
        }
        iteration_logs.append(log_payload)

        try:
            mcp_client.call_tool("postgres", "log_optimization_iteration", log_payload)
        except Exception as exc:
            print(f"  [Offer Optimizer] Iteration logging failed: {exc}")

        if evaluation["objective_score"] > best_eval["objective_score"]:
            best_eval = evaluation
            best_offer = candidate
            best_iteration = iteration_idx

    for log in iteration_logs:
        log["is_selected"] = log["iteration_index"] == best_iteration

    # Re-log selected marker for easy filtering in observability.
    try:
        selected_log = next(
            (item for item in iteration_logs if item["iteration_index"] == best_iteration),
            None,
        )
        if selected_log:
            selected_log_payload = dict(selected_log)
            selected_log_payload["is_selected"] = True
            mcp_client.call_tool("postgres", "log_optimization_iteration", selected_log_payload)
    except Exception as exc:
        print(f"  [Offer Optimizer] Selected iteration logging failed: {exc}")

    best_offer["reason"] = (
        f"{best_offer.get('reason', '')} | optimized in {max_iterations} iterations "
        f"(selected iteration {best_iteration}, objective score {best_eval['objective_score']:.2f})"
    ).strip()

    state["promotion_design"] = best_offer
    state["optimization_iterations"] = iteration_logs
    state["optimization_result"] = {
        "enabled": True,
        "iterations": max_iterations,
        "selected_iteration": best_iteration,
        "selected_objective_score": best_eval["objective_score"],
        "objective": best_eval["objective_name"],
    }

    try:
        mcp_client.call_tool(
            "postgres",
            "log_agent_decision",
            {
                "agent_name": "Offer Optimization Agent",
                "sku_id": state["sku_id"],
                "store_id": state["store_id"],
                "decision_type": "offer_optimization",
                "prompt_fed": None,
                "reasoning": (
                    f"Completed {max_iterations} optimization iterations. "
                    f"Selected iteration {best_iteration} with objective score {best_eval['objective_score']:.2f}."
                ),
                "data_used": {
                    "objective": config.AGENT_CONFIG["optimization_objective"],
                    "iterations": max_iterations,
                    "selected_iteration": best_iteration,
                },
                "decision_outcome": "optimized",
            },
        )
    except Exception as exc:
        print(f"  [Offer Optimizer] Agent decision log failed: {exc}")

    return state

