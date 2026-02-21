import sys
import unittest
from pathlib import Path


LANGGRAPH_DIR = Path(__file__).resolve().parents[1]
if str(LANGGRAPH_DIR) not in sys.path:
    sys.path.append(str(LANGGRAPH_DIR))

from status_targets import compute_status_targets  # noqa: E402


class StatusTargetComputationTests(unittest.TestCase):
    def test_case_a_idle_no_in_progress_uses_cursor_for_next(self):
        result = compute_status_targets(
            targets=[(1, 1), (2, 1)],
            next_target_index=0,
            in_progress_target=None,
            runtime_sku_id=None,
            runtime_store_id=None,
        )

        self.assertIsNone(result["current_target_effective"])
        self.assertEqual(result["next_target"], {"sku_id": 1, "store_id": 1})
        self.assertEqual(result["next_target_after_current"], result["next_target"])

    def test_case_b_in_progress_first_target_next_after_current_is_second(self):
        result = compute_status_targets(
            targets=[(1, 1), (2, 1), (3, 1)],
            next_target_index=0,
            in_progress_target={"sku_id": 1, "store_id": 1},
            runtime_sku_id=1,
            runtime_store_id=1,
        )

        self.assertEqual(result["current_target_effective"], {"sku_id": 1, "store_id": 1})
        self.assertEqual(result["next_target"], {"sku_id": 1, "store_id": 1})
        self.assertEqual(result["next_target_after_current"], {"sku_id": 2, "store_id": 1})

    def test_case_c_in_progress_last_target_next_after_current_is_none(self):
        result = compute_status_targets(
            targets=[(1, 1), (2, 1), (3, 1)],
            next_target_index=2,
            in_progress_target={"sku_id": 3, "store_id": 1},
            runtime_sku_id=3,
            runtime_store_id=1,
        )

        self.assertEqual(result["current_target_effective"], {"sku_id": 3, "store_id": 1})
        self.assertEqual(result["next_target"], {"sku_id": 3, "store_id": 1})
        self.assertIsNone(result["next_target_after_current"])

    def test_case_d_runtime_tracker_fallback_for_current_target(self):
        result = compute_status_targets(
            targets=[(10, 2), (11, 2)],
            next_target_index=1,
            in_progress_target=None,
            runtime_sku_id=10,
            runtime_store_id=2,
        )

        self.assertEqual(result["current_target_effective"], {"sku_id": 10, "store_id": 2})
        self.assertEqual(result["next_target"], {"sku_id": 11, "store_id": 2})
        self.assertEqual(result["next_target_after_current"], {"sku_id": 11, "store_id": 2})

    def test_case_e_empty_targets_returns_nulls(self):
        result = compute_status_targets(
            targets=[],
            next_target_index=0,
            in_progress_target=None,
            runtime_sku_id=None,
            runtime_store_id=None,
        )

        self.assertIsNone(result["current_target_effective"])
        self.assertIsNone(result["next_target"])
        self.assertIsNone(result["next_target_after_current"])


if __name__ == "__main__":
    unittest.main()

