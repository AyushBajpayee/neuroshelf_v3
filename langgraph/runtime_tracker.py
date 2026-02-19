"""
Thread-safe runtime tracker for currently executing agent context.
"""

from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional

_lock = Lock()
_state: Dict[str, Any] = {
    "current_agent": None,
    "sku_id": None,
    "store_id": None,
    "promotion_id": None,
    "updated_at": None,
}


def set_current_agent(
    agent_name: str,
    sku_id: Optional[int] = None,
    store_id: Optional[int] = None,
    promotion_id: Optional[int] = None,
) -> None:
    """Set currently running agent context."""
    with _lock:
        _state["current_agent"] = agent_name
        _state["sku_id"] = sku_id
        _state["store_id"] = store_id
        _state["promotion_id"] = promotion_id
        _state["updated_at"] = datetime.now().isoformat()


def clear_current_agent() -> None:
    """Clear current agent context."""
    with _lock:
        _state["current_agent"] = None
        _state["sku_id"] = None
        _state["store_id"] = None
        _state["promotion_id"] = None
        _state["updated_at"] = datetime.now().isoformat()


def get_runtime_state() -> Dict[str, Any]:
    """Return a copy of runtime state."""
    with _lock:
        return dict(_state)
