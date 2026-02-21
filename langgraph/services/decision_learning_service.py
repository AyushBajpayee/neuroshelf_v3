"""
Decision learning service.
Builds reusable priors from historical promotions and human feedback.
"""

from datetime import datetime
from typing import Any, Dict, List

import config


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


class DecisionLearningService:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

    def get_decision_priors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch latest priors or generate new ones from historical data."""
        if not config.FEATURE_FLAGS["enable_decision_learning"]:
            return {}

        sku_id = state.get("sku_id")
        store_id = state.get("store_id")

        cached = self._get_cached_priors(sku_id=sku_id, store_id=store_id)
        if cached:
            return cached

        generated = self._generate_priors(sku_id=sku_id, store_id=store_id)
        if generated:
            self._persist_priors(
                sku_id=sku_id,
                store_id=store_id,
                priors=generated,
            )
        return generated

    def _get_cached_priors(self, sku_id: int, store_id: int) -> Dict[str, Any]:
        try:
            latest = self.mcp_client.call_tool(
                "postgres",
                "get_latest_decision_prior",
                {"sku_id": sku_id, "store_id": store_id, "max_age_hours": 24 * 14},
            )
            if not latest:
                return {}

            payload = _as_dict(latest.get("prior_payload"))
            if not payload:
                return {}

            payload["source"] = "cached"
            payload["prior_id"] = latest.get("id")
            payload["generated_at"] = payload.get("generated_at") or latest.get("generated_at")
            return payload
        except Exception as exc:
            print(f"  [Decision Learning] Could not fetch cached priors: {exc}")
            return {}

    def _generate_priors(self, sku_id: int, store_id: int) -> Dict[str, Any]:
        try:
            historical_cases = self.mcp_client.call_tool(
                "postgres",
                "get_historical_promotion_cases",
                {"sku_id": sku_id, "store_id": store_id, "limit": 25},
            ) or []
        except Exception as exc:
            print(f"  [Decision Learning] Failed historical case fetch: {exc}")
            historical_cases = []

        feedback_signals: List[Dict[str, Any]] = []
        if config.FEATURE_FLAGS["enable_approval_learning"]:
            try:
                feedback_signals = self.mcp_client.call_tool(
                    "postgres",
                    "get_approval_feedback",
                    {"sku_id": sku_id, "store_id": store_id, "days": 180, "limit": 100},
                ) or []
            except Exception as exc:
                print(f"  [Decision Learning] Failed approval feedback fetch: {exc}")
                feedback_signals = []

        if not historical_cases and not feedback_signals:
            return {}

        successful_cases = [
            case for case in historical_cases
            if float(case.get("avg_performance_ratio", 0) or 0) >= 1.0
        ]
        success_probability = (
            len(successful_cases) / len(historical_cases)
            if historical_cases else 0.5
        )

        approved = sum(1 for signal in feedback_signals if signal.get("reviewer_outcome") == "approved")
        rejected = sum(1 for signal in feedback_signals if signal.get("reviewer_outcome") == "rejected")
        total_feedback = approved + rejected
        approval_rate = (approved / total_feedback) if total_feedback else None

        average_discount = self._safe_average(
            [float(case.get("discount_value", 0) or 0) for case in historical_cases]
        )
        average_margin = self._safe_average(
            [float(case.get("margin_percent", 0) or 0) for case in historical_cases]
        )
        avg_performance_ratio = self._safe_average(
            [float(case.get("avg_performance_ratio", 0) or 0) for case in historical_cases]
        )

        risk_flags: List[str] = []
        if success_probability < 0.40:
            risk_flags.append("historically_low_success")
        if approval_rate is not None and approval_rate < 0.50:
            risk_flags.append("low_human_approval_rate")
        if average_margin and average_margin < config.AGENT_CONFIG["min_margin_percent"] + 2:
            risk_flags.append("margin_pressure")
        if average_discount and average_discount > config.AGENT_CONFIG["max_discount_percent"] * 0.8:
            risk_flags.append("discount_intensity_high")

        confidence = min(
            0.95,
            0.20 + (len(historical_cases) * 0.03) + (total_feedback * 0.02),
        )

        priors = {
            "success_probability": round(success_probability, 4),
            "confidence_score": round(confidence, 4),
            "expected_roi_band": self._to_roi_band(avg_performance_ratio),
            "risk_flags": risk_flags,
            "recommended_discount_range": {
                "min_percent": round(max(0.0, average_discount - 5), 2),
                "max_percent": round(
                    min(config.AGENT_CONFIG["max_discount_percent"], average_discount + 5),
                    2,
                ),
            },
            "evidence": {
                "historical_cases": len(historical_cases),
                "successful_cases": len(successful_cases),
                "approval_feedback_signals": total_feedback,
                "approval_rate": round(approval_rate, 4) if approval_rate is not None else None,
                "average_margin_percent": round(average_margin, 4),
                "average_discount_percent": round(average_discount, 4),
                "average_performance_ratio": round(avg_performance_ratio, 4),
            },
            "source": "generated",
            "generated_at": datetime.now().isoformat(),
        }
        return priors

    def _persist_priors(self, sku_id: int, store_id: int, priors: Dict[str, Any]) -> None:
        try:
            self.mcp_client.call_tool(
                "postgres",
                "create_decision_prior",
                {
                    "sku_id": sku_id,
                    "store_id": store_id,
                    "success_probability": priors.get("success_probability"),
                    "confidence_score": priors.get("confidence_score"),
                    "expected_roi_band": priors.get("expected_roi_band"),
                    "risk_flags": {"flags": priors.get("risk_flags", [])},
                    "prior_payload": priors,
                    "generated_by": "decision_learning_service",
                },
            )
        except Exception as exc:
            print(f"  [Decision Learning] Failed to persist priors: {exc}")

    @staticmethod
    def _safe_average(values: List[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def _to_roi_band(value: float) -> str:
        if value >= 1.2:
            return "high"
        if value >= 0.9:
            return "medium"
        return "low"

