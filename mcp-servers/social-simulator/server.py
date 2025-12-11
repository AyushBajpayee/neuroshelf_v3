"""
MCP Server for Social Media Trends Simulation
Provides realistic social trends and events data
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from simulator import social_sim

# Initialize FastAPI app
app = FastAPI(title="MCP Social Trends Simulator", version="1.0.0")


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
    state = social_sim.get_state()
    return {
        "status": "healthy",
        "service": "mcp-social-simulator",
        "active_trends": state["active_trends_count"],
        "upcoming_events": state["scheduled_events_count"],
    }


# MCP Tool endpoint
@app.post("/tool", response_model=ToolResponse)
def execute_tool(request: ToolRequest):
    """Execute an MCP tool"""
    tool_name = request.tool_name
    parameters = request.parameters

    try:
        if tool_name == "get_trending_topics":
            location_id = parameters.get("location_id")
            result = social_sim.get_trending_topics(location_id)

        elif tool_name == "get_event_calendar":
            location_id = parameters.get("location_id")
            days_ahead = parameters.get("days_ahead", 7)
            result = social_sim.get_event_calendar(location_id, days_ahead)

        elif tool_name == "check_sku_sentiment":
            sku_category = parameters.get("sku_category")
            if not sku_category:
                raise ValueError("sku_category is required")
            result = social_sim.check_sku_sentiment(sku_category)

        elif tool_name == "inject_viral_moment":
            topic = parameters.get("topic")
            intensity = parameters.get("intensity", 80)
            if not topic:
                raise ValueError("topic is required")
            result = social_sim.inject_viral_moment(topic, intensity)

        elif tool_name == "create_event":
            event_name = parameters.get("event_name")
            event_type = parameters.get("event_type")
            location_id = parameters.get("location_id")
            start_time = parameters.get("start_time")
            attendance = parameters.get("attendance", 1000)
            if not all([event_name, event_type, location_id, start_time]):
                raise ValueError(
                    "event_name, event_type, location_id, and start_time are required"
                )
            result = social_sim.create_event(
                event_name, event_type, location_id, start_time, attendance
            )

        elif tool_name == "get_simulator_state":
            result = social_sim.get_state()

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return ToolResponse(success=True, data=result)

    except Exception as e:
        return ToolResponse(success=False, data=None, error=str(e))


# Additional REST endpoints for UI control
@app.get("/trending")
def get_trending(location_id: Optional[int] = None):
    """Get trending topics"""
    return social_sim.get_trending_topics(location_id)


@app.get("/events")
def get_events(location_id: Optional[int] = None, days_ahead: int = 7):
    """Get event calendar"""
    return social_sim.get_event_calendar(location_id, days_ahead)


@app.get("/sentiment/{category}")
def get_sentiment(category: str):
    """Get SKU category sentiment"""
    return social_sim.check_sku_sentiment(category)


@app.post("/viral")
def inject_viral(topic: str, intensity: int = 80):
    """Inject viral moment"""
    return social_sim.inject_viral_moment(topic, intensity)


@app.get("/state")
def get_state():
    """Get simulator state"""
    return social_sim.get_state()


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("Starting MCP Social Trends Simulator...")
    state = social_sim.get_state()
    print(f"Active trends: {state['active_trends_count']}")
    print(f"Scheduled events: {state['scheduled_events_count']}")
    uvicorn.run(app, host="0.0.0.0", port=3003)
