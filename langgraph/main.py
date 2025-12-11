"""
LangGraph Main Entry Point
Autonomous pricing intelligence agent orchestration
"""

import os
import asyncio
import time
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI
import uvicorn

# Set environment variables for LangSmith
if os.getenv("LANGSMITH_TRACING"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
    os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "pricing-intelligence-agent")

import config
from mcp_client import mcp_client
from graph import create_pricing_graph, create_monitoring_graph

# Initialize FastAPI for health checks and API
app = FastAPI(title="LangGraph Pricing Agent", version="1.0.0")

# Initialize graphs
pricing_graph = create_pricing_graph()
monitoring_graph = create_monitoring_graph()

# Agent state
agent_state = {
    "running": False,
    "last_run": None,
    "cycles_completed": 0,
    "errors": [],
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
    return agent_state


@app.post("/trigger")
def trigger_analysis(sku_id: int, store_id: int):
    """Manually trigger analysis for a specific SKU/store"""
    try:
        result = run_pricing_analysis(sku_id, store_id)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_skus_and_stores() -> List[Dict]:
    """Get all SKU and store combinations to analyze"""
    try:
        # Get inventory from database
        inventory = mcp_client.call_tool(
            "postgres", "query_inventory_levels", {}
        )
        return [
            {"sku_id": item["sku_id"], "store_id": item["store_id"]}
            for item in inventory
        ]
    except Exception as e:
        print(f"Error getting SKUs and stores: {e}")
        return []


def run_pricing_analysis(sku_id: int, store_id: int) -> Dict:
    """Run pricing analysis for a single SKU at a store"""
    try:
        print(f"Analyzing SKU {sku_id} at Store {store_id}...")

        # Initialize state
        initial_state = {
            "sku_id": sku_id,
            "store_id": store_id,
            "messages": [],
            "should_act": False,
        }

        # Run the graph
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
        agent_state["errors"].append(
            {"sku_id": sku_id, "store_id": store_id, "error": str(e), "timestamp": datetime.now().isoformat()}
        )
        return {"error": str(e)}


def monitor_active_promotions():
    """Monitor all active promotions and retract if necessary"""
    try:
        # Get active promotions
        active_promotions = mcp_client.call_tool(
            "postgres", "get_active_promotions", {}
        )

        print(f"Monitoring {len(active_promotions)} active promotions...")

        for promo in active_promotions:
            # Initialize monitoring state
            state = {
                "promotion_id": promo["id"],
                "sku_id": promo["sku_id"],
                "store_id": promo["store_id"],
                "messages": [],
            }

            # Run monitoring graph
            monitoring_graph.invoke(state)

    except Exception as e:
        print(f"Error monitoring promotions: {e}")


async def agent_loop():
    """Main agent loop - runs continuously"""
    print("Starting agent loop...")
    agent_state["running"] = True

    interval_minutes = config.AGENT_CONFIG["monitoring_interval_minutes"]
    interval_seconds = interval_minutes * 60

    while True:
        try:
            cycle_start = time.time()
            print(f"\n{'='*60}")
            print(f"Agent Cycle Starting at {datetime.now()}")
            print(f"{'='*60}")

            # Get all SKU/store combinations
            targets = get_all_skus_and_stores()
            print(f"Analyzing {len(targets)} SKU/store combinations...")

            # Analyze each target (in production, consider parallelization)
            # For now, we'll sample a subset to avoid overwhelming the system
            sample_size = min(10, len(targets))
            sample_targets = targets[:sample_size]

            for target in sample_targets:
                run_pricing_analysis(target["sku_id"], target["store_id"])
                await asyncio.sleep(1)  # Small delay between analyses

            # Monitor active promotions
            monitor_active_promotions()

            # Update agent state
            agent_state["last_run"] = datetime.now().isoformat()
            agent_state["cycles_completed"] += 1

            cycle_duration = time.time() - cycle_start
            print(f"\nCycle completed in {cycle_duration:.2f} seconds")
            print(f"Next cycle in {interval_minutes} minutes")

            # Wait until next cycle
            await asyncio.sleep(interval_seconds)

        except Exception as e:
            print(f"Error in agent loop: {e}")
            agent_state["errors"].append({"error": str(e), "timestamp": datetime.now().isoformat()})
            await asyncio.sleep(60)  # Wait 1 minute before retrying


@app.on_event("startup")
async def startup_event():
    """Start the agent loop when the app starts"""
    # Verify MCP connections
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

        # Start agent loop in background
        asyncio.create_task(agent_loop())

    except Exception as e:
        print(f"Startup error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    agent_state["running"] = False
    mcp_client.close()


if __name__ == "__main__":
    print("="*60)
    print("Pricing Intelligence Agent System")
    print("="*60)
    print(f"Model: {config.OPENAI_CONFIG['model']}")
    print(f"LangSmith Tracing: {config.LANGSMITH_CONFIG['tracing']}")
    print("="*60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
