"""
LangGraph Main Entry Point
Autonomous pricing intelligence agent orchestration
"""

import asyncio
import os
from contextlib import suppress
from datetime import datetime
from typing import Dict, List, Tuple

from fastapi import FastAPI
import uvicorn

# Set environment variables for LangSmith
if os.getenv("LANGSMITH_TRACING"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "pricing-intelligence-agent")

import config
from graph import create_monitoring_graph, create_pricing_graph
from mcp_client import mcp_client
from runtime_tracker import clear_current_agent, get_runtime_state, set_current_agent

DEFAULT_SKUS = list(range(1, 21))
DEFAULT_STORES = list(range(1, 6))

# Initialize FastAPI for health checks and API
app = FastAPI(title="LangGraph Pricing Agent", version="1.0.0")

# Initialize graphs
pricing_graph = create_pricing_graph()
monitoring_graph = create_monitoring_graph()


def parse_id_list(raw_values: str) -> List[int]:
    """Parse comma-separated IDs into a deduplicated list."""
    ids: List[int] = []
    seen = set()
    for raw in raw_values.split(","):
        value = raw.strip()
        if not value:
            continue
        try:
            parsed = int(value)
            if parsed <= 0:
                continue
            if parsed not in seen:
                ids.append(parsed)
                seen.add(parsed)
        except ValueError:
            print(f"Ignoring invalid ID value: {value}")
    return ids


def build_target_pairs() -> List[Tuple[int, int]]:
    """
    Build deterministic scan order of (sku_id, store_id) pairs.
    Uses env-configured subsets when present; otherwise defaults to 20x5 grid.
    """
    skus_raw = config.SKUS_CONSIDERED or os.getenv("SKUS_CONSIDERED", "")
    stores_raw = config.STORES_CONSIDERED or os.getenv("STORES_CONSIDERED", "")

    skus = parse_id_list(skus_raw) or DEFAULT_SKUS
    stores = parse_id_list(stores_raw) or DEFAULT_STORES

    return [(sku_id, store_id) for store_id in stores for sku_id in skus]


AGENT_TARGETS = build_target_pairs()
AUTO_START_ENABLED = os.getenv("AGENT_AUTO_START", "false").lower() == "true"

# Agent state
agent_state = {
    "running": AUTO_START_ENABLED,
    "last_run": None,
    "cycles_completed": 0,
    "errors": [],
    "next_target_index": 0,  # Resume cursor within AGENT_TARGETS
    "cycle_started_at": None,
    "last_processed_target": None,
    "in_progress_target": None,
}


def append_error(error_payload: Dict) -> None:
    """Add an error entry and keep only recent history."""
    agent_state["errors"].append(error_payload)
    if len(agent_state["errors"]) > 100:
        agent_state["errors"] = agent_state["errors"][-100:]


def get_status_payload() -> Dict:
    """Build serializable status payload."""
    runtime_state = get_runtime_state()
    total_targets = len(AGENT_TARGETS)
    next_target = None
    next_index = agent_state["next_target_index"]
    if total_targets > 0 and next_index < total_targets:
        sku_id, store_id = AGENT_TARGETS[next_index]
        next_target = {"sku_id": sku_id, "store_id": store_id}

    task = getattr(app.state, "agent_loop_task", None)
    worker_running = bool(task and not task.done())

    return {
        "running": agent_state["running"],
        "worker_running": worker_running,
        "last_run": agent_state["last_run"],
        "cycles_completed": agent_state["cycles_completed"],
        "next_target_index": next_index,
        "targets_in_cycle": total_targets,
        "next_target": next_target,
        "last_processed_target": agent_state["last_processed_target"],
        "in_progress_target": agent_state["in_progress_target"],
        "cycle_started_at": agent_state["cycle_started_at"],
        "current_agent": runtime_state.get("current_agent"),
        "current_sku_id": runtime_state.get("sku_id"),
        "current_store_id": runtime_state.get("store_id"),
        "current_promotion_id": runtime_state.get("promotion_id"),
        "current_agent_updated_at": runtime_state.get("updated_at"),
        "errors": agent_state["errors"][-10:],
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "langgraph-core",
        "agent_running": agent_state["running"],
        "last_run": agent_state["last_run"],
        "cycles_completed": agent_state["cycles_completed"],
    }


@app.get("/status")
def get_status():
    """Get detailed agent status"""
    return get_status_payload()


@app.post("/agent/start")
def start_agent():
    """Start/resume autonomous loop from current cursor."""
    if not AGENT_TARGETS:
        return {
            "success": False,
            "message": "No agent targets configured.",
            "status": get_status_payload(),
        }

    if agent_state["running"]:
        return {
            "success": True,
            "message": "Agent loop already running.",
            "status": get_status_payload(),
        }

    agent_state["running"] = True

    return {
        "success": True,
        "message": "Agent loop started.",
        "status": get_status_payload(),
    }


@app.post("/agent/stop")
def stop_agent():
    """
    Pause autonomous loop.
    Loop resumes from the same cursor on /agent/start.
    """
    agent_state["running"] = False
    return {
        "success": True,
        "message": "Agent loop paused.",
        "status": get_status_payload(),
    }


@app.post("/trigger")
def trigger_analysis(sku_id: int, store_id: int):
    """Manually trigger analysis for a specific SKU/store"""
    try:
        result = run_pricing_analysis(sku_id, store_id)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_pricing_analysis(sku_id: int, store_id: int) -> Dict:
    """Run pricing analysis for a single SKU at a store"""
    try:
        print(f"Analyzing SKU {sku_id} at Store {store_id}...")
        set_current_agent("Pricing Graph", sku_id=sku_id, store_id=store_id)

        initial_state = {
            "sku_id": sku_id,
            "store_id": store_id,
            "messages": [],
            "should_act": False,
        }

        result = pricing_graph.invoke(initial_state)

        return {
            "sku_id": sku_id,
            "store_id": store_id,
            "should_act": result.get("should_act", False),
            "promotion_id": result.get("promotion_id"),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Error in pricing analysis: {e}")
        append_error(
            {
                "sku_id": sku_id,
                "store_id": store_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        )
        return {"error": str(e)}
    finally:
        clear_current_agent()


def monitor_active_promotions():
    """Monitor all active promotions and retract if necessary"""
    try:
        set_current_agent("Monitoring Graph")
        active_promotions = mcp_client.call_tool("postgres", "get_active_promotions", {})

        print(f"Monitoring {len(active_promotions)} active promotions...")

        for promo in active_promotions:
            state = {
                "promotion_id": promo["id"],
                "sku_id": promo["sku_id"],
                "store_id": promo["store_id"],
                "messages": [],
            }
            monitoring_graph.invoke(state)

    except Exception as e:
        print(f"Error monitoring promotions: {e}")
        append_error(
            {
                "error": f"monitor_active_promotions: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }
        )
    finally:
        clear_current_agent()


async def sleep_interruptible(seconds: int):
    """Sleep while allowing pause to take effect quickly."""
    elapsed = 0
    while elapsed < seconds:
        if not agent_state["running"]:
            return
        await asyncio.sleep(1)
        elapsed += 1


async def agent_loop():
    """
    Background worker.
    Executes continuously, but only processes targets when agent_state['running'] is True.
    """
    print("Starting agent worker...")
    interval_minutes = config.AGENT_CONFIG["monitoring_interval_minutes"]
    interval_seconds = max(1, int(interval_minutes * 60))

    while True:
        try:
            if not agent_state["running"]:
                await asyncio.sleep(1)
                continue

            if not AGENT_TARGETS:
                print("No targets configured. Waiting for configuration...")
                await asyncio.sleep(5)
                continue

            total_targets = len(AGENT_TARGETS)
            if agent_state["next_target_index"] >= total_targets:
                agent_state["next_target_index"] = 0

            if not agent_state["cycle_started_at"]:
                agent_state["cycle_started_at"] = datetime.now().isoformat()
                print(f"\n{'=' * 60}")
                print(f"Agent Cycle Starting at {agent_state['cycle_started_at']}")
                print(f"Targets this cycle: {total_targets}")
                print(f"{'=' * 60}")

            while agent_state["next_target_index"] < total_targets:
                if not agent_state["running"]:
                    print("Agent paused. Waiting for resume signal...")
                    break

                idx = agent_state["next_target_index"]
                sku_id, store_id = AGENT_TARGETS[idx]
                agent_state["in_progress_target"] = {"sku_id": sku_id, "store_id": store_id}

                # Run CPU/network-heavy analysis off the event loop so API endpoints stay responsive.
                await asyncio.to_thread(run_pricing_analysis, sku_id, store_id)
                agent_state["last_processed_target"] = {"sku_id": sku_id, "store_id": store_id}
                agent_state["next_target_index"] = idx + 1
                agent_state["in_progress_target"] = None

                await asyncio.sleep(1)

            if not agent_state["running"]:
                continue

            # Monitoring performs blocking MCP/graph work; keep it off the event loop.
            await asyncio.to_thread(monitor_active_promotions)

            cycle_started = datetime.fromisoformat(agent_state["cycle_started_at"])
            cycle_duration = (datetime.now() - cycle_started).total_seconds()

            agent_state["last_run"] = datetime.now().isoformat()
            agent_state["cycles_completed"] += 1
            agent_state["next_target_index"] = 0
            agent_state["cycle_started_at"] = None
            agent_state["in_progress_target"] = None

            print(f"\nCycle completed in {cycle_duration:.2f} seconds")
            print(f"Next cycle in {interval_minutes} minutes")

            await sleep_interruptible(interval_seconds)

        except asyncio.CancelledError:
            print("Agent worker cancelled.")
            raise
        except Exception as e:
            print(f"Error in agent loop: {e}")
            append_error({"error": str(e), "timestamp": datetime.now().isoformat()})
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start background worker. Agent auto-run depends on AGENT_AUTO_START."""
    try:
        print("Verifying MCP server connections...")
        for server_name, url in config.MCP_SERVERS.items():
            print(f"  - {server_name}: {url}")

        print("\nAgent Configuration:")
        print(f"  - Monitoring Interval: {config.AGENT_CONFIG['monitoring_interval_minutes']} minutes")
        print(f"  - Min Margin: {config.AGENT_CONFIG['min_margin_percent']}%")
        print(f"  - Max Discount: {config.AGENT_CONFIG['max_discount_percent']}%")
        print(f"  - Auto Retract Threshold: {config.AGENT_CONFIG['auto_retract_threshold']}")
        print(f"  - Manual Approval Required: {config.AGENT_CONFIG['require_manual_approval']}")
        print(f"  - Auto Start Enabled: {AUTO_START_ENABLED}")
        print(f"  - Target Count: {len(AGENT_TARGETS)}")

        app.state.agent_loop_task = asyncio.create_task(agent_loop())

        if AUTO_START_ENABLED:
            print("Agent loop will start processing immediately.")
        else:
            print("Agent loop is paused by default. Use /agent/start or Streamlit control button.")

    except Exception as e:
        print(f"Startup error: {e}")
        append_error({"error": f"startup_event: {str(e)}", "timestamp": datetime.now().isoformat()})


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    agent_state["running"] = False

    loop_task = getattr(app.state, "agent_loop_task", None)
    if loop_task:
        loop_task.cancel()
        with suppress(asyncio.CancelledError):
            await loop_task

    mcp_client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Pricing Intelligence Agent System")
    print("=" * 60)
    print(f"Model: {config.OPENAI_CONFIG['model']}")
    print(f"LangSmith Tracing: {config.LANGSMITH_CONFIG['tracing']}")
    print(f"Auto Start: {AUTO_START_ENABLED}")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
