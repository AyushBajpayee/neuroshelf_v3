"""
MCP Server for Competitor Pricing Simulation
Provides realistic competitor pricing data
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from simulator import competitor_sim

# Initialize FastAPI app
app = FastAPI(title="MCP Competitor Pricing Simulator", version="1.0.0")


# Pydantic models
class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class ToolResponse(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mcp-competitor-simulator",
        "competitor_count": len(competitor_sim.get_state()["competitors"]),
    }


# MCP Tool endpoint
@app.post("/tool", response_model=ToolResponse)
def execute_tool(request: ToolRequest):
    """Execute an MCP tool"""
    tool_name = request.tool_name
    parameters = request.parameters

    try:
        if tool_name == "get_competitor_prices":
            sku_id = parameters.get("sku_id")
            location_id = parameters.get("location_id")
            if sku_id is None:
                raise ValueError("sku_id is required")
            result = competitor_sim.get_competitor_prices(sku_id, location_id)

        elif tool_name == "get_competitor_history":
            sku_id = parameters.get("sku_id")
            days_back = parameters.get("days_back", 7)
            if sku_id is None:
                raise ValueError("sku_id is required")
            result = competitor_sim.get_competitor_history(sku_id, days_back)

        elif tool_name == "trigger_competitor_promo":
            competitor_name = parameters.get("competitor_name")
            sku_id = parameters.get("sku_id")
            discount_percent = parameters.get("discount_percent")
            if not all([competitor_name, sku_id, discount_percent]):
                raise ValueError(
                    "competitor_name, sku_id, and discount_percent are required"
                )
            result = competitor_sim.trigger_competitor_promo(
                competitor_name, sku_id, discount_percent
            )

        elif tool_name == "end_competitor_promo":
            competitor_name = parameters.get("competitor_name")
            sku_id = parameters.get("sku_id")
            if not all([competitor_name, sku_id]):
                raise ValueError("competitor_name and sku_id are required")
            result = competitor_sim.end_competitor_promo(competitor_name, sku_id)

        elif tool_name == "react_to_our_promotion":
            sku_id = parameters.get("sku_id")
            our_price = parameters.get("our_price")
            if not all([sku_id, our_price]):
                raise ValueError("sku_id and our_price are required")
            result = competitor_sim.react_to_our_promotion(sku_id, our_price)

        elif tool_name == "update_competitor_strategy":
            competitor_name = parameters.get("competitor_name")
            new_strategy = parameters.get("new_strategy")
            if not all([competitor_name, new_strategy]):
                raise ValueError("competitor_name and new_strategy are required")
            result = competitor_sim.update_strategy(competitor_name, new_strategy)

        elif tool_name == "get_simulator_state":
            result = competitor_sim.get_state()

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return ToolResponse(success=True, data=result)

    except Exception as e:
        return ToolResponse(success=False, data=None, error=str(e))


# Additional REST endpoints for UI control
@app.get("/prices/{sku_id}")
def get_prices(sku_id: int, location_id: Optional[int] = None):
    """Get competitor prices for SKU"""
    return competitor_sim.get_competitor_prices(sku_id, location_id)


@app.get("/history/{sku_id}")
def get_history(sku_id: int, days: int = 7):
    """Get competitor price history"""
    return competitor_sim.get_competitor_history(sku_id, days)


@app.post("/promotion/trigger")
def trigger_promotion(competitor_name: str, sku_id: int, discount_percent: float):
    """Trigger competitor promotion"""
    return competitor_sim.trigger_competitor_promo(
        competitor_name, sku_id, discount_percent
    )


@app.post("/promotion/end")
def end_promotion(competitor_name: str, sku_id: int):
    """End competitor promotion"""
    return competitor_sim.end_competitor_promo(competitor_name, sku_id)


@app.get("/state")
def get_state():
    """Get simulator state"""
    return competitor_sim.get_state()


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("Starting MCP Competitor Pricing Simulator...")
    print(f"Configured competitors: {list(competitor_sim.get_state()['competitors'].keys())}")
    uvicorn.run(app, host="0.0.0.0", port=3002)
