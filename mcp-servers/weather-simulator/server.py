"""
MCP Server for Weather Simulation
Provides realistic weather data for pricing decisions
"""

import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from simulator import weather_sim

# Initialize FastAPI app
app = FastAPI(title="MCP Weather Simulator", version="1.0.0")


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
        "service": "mcp-weather-simulator",
        "current_season": weather_sim.get_current_season(),
    }


# MCP Tool endpoint
@app.post("/tool", response_model=ToolResponse)
def execute_tool(request: ToolRequest):
    """Execute an MCP tool"""
    tool_name = request.tool_name
    parameters = request.parameters

    try:
        if tool_name == "get_current_weather":
            location_id = parameters.get("location_id")
            if location_id is None:
                raise ValueError("location_id is required")
            result = weather_sim.get_current_weather(location_id)

        elif tool_name == "get_weather_forecast":
            location_id = parameters.get("location_id")
            hours_ahead = parameters.get("hours_ahead", 24)
            if location_id is None:
                raise ValueError("location_id is required")
            result = weather_sim.get_weather_forecast(location_id, hours_ahead)

        elif tool_name == "set_weather_scenario":
            location_id = parameters.get("location_id")
            scenario = parameters.get("scenario")
            duration_hours = parameters.get("duration_hours", 24)
            if location_id is None or scenario is None:
                raise ValueError("location_id and scenario are required")
            result = weather_sim.set_weather_scenario(
                location_id, scenario, duration_hours
            )

        elif tool_name == "get_simulator_state":
            result = weather_sim.get_state()

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return ToolResponse(success=True, data=result)

    except Exception as e:
        return ToolResponse(success=False, data=None, error=str(e))


# Additional REST endpoints for UI control
@app.get("/weather/{location_id}")
def get_weather(location_id: int):
    """Get current weather for a location"""
    return weather_sim.get_current_weather(location_id)


@app.get("/forecast/{location_id}")
def get_forecast(location_id: int, hours: int = 24):
    """Get weather forecast"""
    return weather_sim.get_weather_forecast(location_id, hours)


@app.post("/scenario")
def set_scenario(location_id: int, scenario: str, duration_hours: int = 24):
    """Set weather scenario"""
    return weather_sim.set_weather_scenario(location_id, scenario, duration_hours)


@app.get("/state")
def get_state():
    """Get simulator state"""
    return weather_sim.get_state()


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("Starting MCP Weather Simulator...")
    print(f"Current season: {weather_sim.get_current_season()}")
    uvicorn.run(app, host="0.0.0.0", port=3001)
