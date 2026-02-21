"""Utilities for computing target fields in /status payloads."""

from typing import Dict, List, Optional, Tuple


TargetPair = Tuple[int, int]
TargetPayload = Optional[Dict[str, int]]


def _to_target_payload(sku_id: int, store_id: int) -> Dict[str, int]:
    return {"sku_id": sku_id, "store_id": store_id}


def _is_valid_target_payload(target: Dict) -> bool:
    if not isinstance(target, dict):
        return False
    return target.get("sku_id") is not None and target.get("store_id") is not None


def _cursor_target(targets: List[TargetPair], next_target_index: int) -> TargetPayload:
    if 0 <= next_target_index < len(targets):
        sku_id, store_id = targets[next_target_index]
        return _to_target_payload(sku_id, store_id)
    return None


def compute_status_targets(
    targets: List[TargetPair],
    next_target_index: int,
    in_progress_target: Dict,
    runtime_sku_id: Optional[int],
    runtime_store_id: Optional[int],
) -> Dict[str, TargetPayload]:
    """
    Compute target fields for /status payload.

    Semantics:
    - next_target: cursor target (legacy behavior).
    - current_target_effective: in_progress target first, runtime fallback second.
    - next_target_after_current:
      - if in_progress_target exists, return index+1 when available; otherwise None.
      - if no in_progress_target, same as next_target.
    """
    next_target = _cursor_target(targets, next_target_index)

    if _is_valid_target_payload(in_progress_target):
        current_target_effective: TargetPayload = {
            "sku_id": int(in_progress_target["sku_id"]),
            "store_id": int(in_progress_target["store_id"]),
        }
    elif runtime_sku_id is not None and runtime_store_id is not None:
        current_target_effective = _to_target_payload(int(runtime_sku_id), int(runtime_store_id))
    else:
        current_target_effective = None

    if _is_valid_target_payload(in_progress_target):
        next_after_index = next_target_index + 1
        next_target_after_current = _cursor_target(targets, next_after_index)
    else:
        next_target_after_current = next_target

    return {
        "next_target": next_target,
        "current_target_effective": current_target_effective,
        "next_target_after_current": next_target_after_current,
    }

