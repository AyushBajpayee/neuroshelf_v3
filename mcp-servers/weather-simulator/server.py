"""
MCP Server for Weather Simulation
Provides realistic weather data for pricing decisions
"""

from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from simulator import weather_sim

# Initialize MCP Server
mcp = FastMCP("MCP Weather Simulator")

# Note: ToolRequest and ToolResponse models removed - FastMCP uses function parameters directly


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@mcp.tool()
def health_check() -> dict:
    """
    Check weather simulator health status.
    """
    return {
        "status": "healthy",
        "service": "mcp-weather-simulator",
        "current_season": weather_sim.get_current_season(),
    }


@mcp.tool()
def get_current_weather(location_id: int) -> Dict[str, Any]:
    """
    Get current weather conditions for a location.
    
    Args:
        location_id: The location ID to get weather for
    """
    return weather_sim.get_current_weather(location_id)


@mcp.tool()
def get_weather_forecast(location_id: int, hours_ahead: int = 24) -> List[Dict[str, Any]]:
    """
    Get weather forecast for a location.
    
    Args:
        location_id: The location ID to get forecast for
        hours_ahead: Number of hours ahead to forecast (default: 24)
    """
    return weather_sim.get_weather_forecast(location_id, hours_ahead)


@mcp.tool()
def set_weather_scenario(location_id: int, scenario: str, duration_hours: int = 24) -> Dict[str, Any]:
    """
    Set a specific weather scenario for testing.
    
    Args:
        location_id: The location ID to set weather for
        scenario: Weather scenario name (e.g., "heat_wave", "cold_snap", "rainy")
        duration_hours: Duration of the scenario in hours (default: 24)
    """
    return weather_sim.set_weather_scenario(location_id, scenario, duration_hours)


@mcp.tool()
def get_simulator_state() -> Dict:
    """
    Get current simulator state including active weather scenarios.
    """
    return weather_sim.get_state()


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("Starting MCP Weather Simulator...")
    print(f"Current season: {weather_sim.get_current_season()}")
    mcp.run()
 