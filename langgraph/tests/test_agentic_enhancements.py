import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


LANGGRAPH_DIR = Path(__file__).resolve().parents[1]
if str(LANGGRAPH_DIR) not in sys.path:
    sys.path.append(str(LANGGRAPH_DIR))

# Lightweight httpx stub for environments without project deps installed.
if "httpx" not in sys.modules:
    httpx_stub = types.ModuleType("httpx")

    class _DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            raise RuntimeError("httpx stub client should not be used in unit tests.")

        def close(self):
            pass

    httpx_stub.Client = _DummyClient
    httpx_stub.HTTPError = Exception
    sys.modules["httpx"] = httpx_stub

from agents import multi_critic, offer_optimizer  # noqa: E402
import config as lg_config  # noqa: E402
from services.decision_learning_service import DecisionLearningService  # noqa: E402
from services.rag_similarity_service import SimilarityRetrievalService  # noqa: E402


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    def call_tool(self, server_name, tool_name, parameters):
        self.calls.append((server_name, tool_name, parameters))

        if tool_name == "get_latest_decision_prior":
            return {}
        if tool_name == "get_historical_promotion_cases":
            return [
                {
                    "promotion_id": 101,
                    "sku_id": 1,
                    "store_id": 1,
                    "discount_value": 12,
                    "margin_percent": 18,
                    "avg_performance_ratio": 1.25,
                    "promotion_type": "discount",
                    "status": "completed",
                    "reason": "test-case",
                },
                {
                    "promotion_id": 102,
                    "sku_id": 1,
                    "store_id": 1,
                    "discount_value": 20,
                    "margin_percent": 14,
                    "avg_performance_ratio": 0.8,
                    "promotion_type": "flash_sale",
                    "status": "completed",
                    "reason": "test-case-2",
                },
            ]
        if tool_name == "get_approval_feedback":
            return [{"reviewer_outcome": "approved"}, {"reviewer_outcome": "rejected"}]
        return {}


class AgenticEnhancementTests(unittest.TestCase):
    def test_offer_optimization_disabled_keeps_single_pass(self):
        state = {
            "sku_id": 1,
            "store_id": 1,
            "promotion_design": {
                "promotion_type": "discount",
                "original_price": 10.0,
                "promotional_price": 9.0,
                "discount_value": 10.0,
                "expected_units_sold": 12,
            },
            "inventory_data": {"base_cost": 6.0},
        }

        with patch.dict(offer_optimizer.config.FEATURE_FLAGS, {"enable_optimization_loop": False}, clear=False):
            result = offer_optimizer.optimize_offer_node(dict(state))

        self.assertFalse(result["optimization_result"]["enabled"])
        self.assertEqual(result["promotion_design"]["discount_value"], 10.0)

    def test_offer_optimization_enabled_logs_iterations(self):
        state = {
            "sku_id": 1,
            "store_id": 1,
            "promotion_design": {
                "promotion_type": "discount",
                "original_price": 10.0,
                "promotional_price": 9.0,
                "discount_value": 10.0,
                "expected_units_sold": 10,
                "reason": "baseline design",
            },
            "inventory_data": {"base_cost": 6.0},
        }

        fake_mcp = MagicMock()
        with patch.dict(offer_optimizer.config.FEATURE_FLAGS, {"enable_optimization_loop": True}, clear=False), \
             patch.dict(offer_optimizer.config.AGENT_CONFIG, {"optimization_max_iterations": 3}, clear=False), \
             patch.object(offer_optimizer, "mcp_client", fake_mcp):
            result = offer_optimizer.optimize_offer_node(dict(state))

        iteration_calls = [
            call for call in fake_mcp.call_tool.call_args_list
            if call.args[1] == "log_optimization_iteration"
        ]
        self.assertGreaterEqual(len(iteration_calls), 3)
        self.assertTrue(result["optimization_result"]["enabled"])
        self.assertEqual(result["optimization_result"]["iterations"], 3)

    def test_multi_critic_disabled_bypasses_stage(self):
        state = {
            "sku_id": 1,
            "store_id": 1,
            "promotion_design": {"discount_value": 10, "promotion_type": "discount"},
        }
        with patch.dict(multi_critic.config.FEATURE_FLAGS, {"enable_multi_critic": False}, clear=False):
            result = multi_critic.multi_critic_review_node(dict(state))

        self.assertEqual(result["critic_decision"]["action"], "approve")
        self.assertFalse(result["critic_decision"]["enabled"])

    def test_multi_critic_enabled_logs_scores(self):
        state = {
            "sku_id": 1,
            "store_id": 1,
            "sell_through_rate": {"avg_daily_sales": 20},
            "inventory_data": {"base_cost": 8.5},
            "promotion_design": {
                "promotion_type": "discount",
                "original_price": 10.0,
                "promotional_price": 9.0,
                "discount_value": 10.0,
                "margin_percent": 12.0,
                "expected_units_sold": 35,
                "reason": "test",
            },
        }

        fake_mcp = MagicMock()
        with patch.dict(multi_critic.config.FEATURE_FLAGS, {"enable_multi_critic": True}, clear=False), \
             patch.object(multi_critic, "mcp_client", fake_mcp):
            result = multi_critic.multi_critic_review_node(dict(state))

        evaluator_calls = [
            call for call in fake_mcp.call_tool.call_args_list
            if call.args[1] == "log_evaluator_score"
        ]
        self.assertEqual(len(evaluator_calls), 3)
        self.assertIn(result["critic_decision"]["action"], {"approve", "revise", "reject"})

    def test_decision_learning_generates_and_persists_priors(self):
        fake_mcp = FakeMCPClient()
        service = DecisionLearningService(fake_mcp)
        state = {"sku_id": 1, "store_id": 1}

        with patch.dict(lg_config.FEATURE_FLAGS, {
            "enable_decision_learning": True,
            "enable_approval_learning": True,
        }, clear=False):
            priors = service.get_decision_priors(state)

        self.assertIn("success_probability", priors)
        called_tools = [tool_name for _, tool_name, _ in fake_mcp.calls]
        self.assertIn("create_decision_prior", called_tools)

    def test_rag_similarity_fallback_includes_spinup_plan(self):
        fake_mcp = FakeMCPClient()
        service = SimilarityRetrievalService(fake_mcp)
        state = {
            "sku_id": 1,
            "store_id": 1,
            "inventory_data": {"category": "beverages"},
            "sell_through_rate": {"avg_daily_sales": 12},
            "weather_data": {"condition": "hot"},
            "social_data": {"has_buzz": True},
            "competitor_data": [{"name": "CompA"}],
        }

        with patch.dict(lg_config.FEATURE_FLAGS, {"enable_rag_similarity": True}, clear=False), \
             patch.object(service, "_get_chroma_collection", side_effect=RuntimeError("chroma offline")):
            output = service.retrieve_similar_cases(state)

        self.assertEqual(output["stats"]["method"], "postgres_fallback")
        self.assertGreaterEqual(len(output["plan"]), 1)
        self.assertGreaterEqual(output["stats"]["hits"], 1)


if __name__ == "__main__":
    unittest.main()
