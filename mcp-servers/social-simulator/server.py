"""
MCP Server for Social Media Trends Simulation
Provides realistic social trends and events data
"""

from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from simulator import social_sim

# Initialize MCP Server
mcp = FastMCP("MCP Social Trends Simulator")

# Note: ToolRequest and ToolResponse models removed - FastMCP uses function parameters directly


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@mcp.tool()
def health_check() -> dict:
    """
    Check social simulator health status.
    """
    state = social_sim.get_state()
    return {
        "status": "healthy",
        "service": "mcp-social-simulator",
        "active_trends": state["active_trends_count"],
        "upcoming_events": state["scheduled_events_count"],
    }


@mcp.tool()
def get_trending_topics(location_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get current trending topics on social media.
    
    Args:
        location_id: Optional location ID to filter trends by location
    """
    return social_sim.get_trending_topics(location_id)


@mcp.tool()
def get_event_calendar(location_id: Optional[int] = None, days_ahead: int = 7) -> List[Dict[str, Any]]:
    """
    Get upcoming events calendar.
    
    Args:
        location_id: Optional location ID to filter events by location
        days_ahead: Number of days ahead to look for events (default: 7)
    """
    return social_sim.get_event_calendar(location_id, days_ahead)


@mcp.tool()
def check_sku_sentiment(sku_category: str) -> Dict[str, Any]:
    """
    Check sentiment/buzz for a SKU category.
    
    Args:
        sku_category: The SKU category to check sentiment for
    """
    return social_sim.check_sku_sentiment(sku_category)


@mcp.tool()
def inject_viral_moment(topic: str, intensity: int = 80) -> Dict[str, Any]:
    """
    Manually inject a viral moment/topic.
    
    Args:
        topic: The topic name to make viral
        intensity: Intensity level (0-100, default: 80)
    """
    return social_sim.inject_viral_moment(topic, intensity)


@mcp.tool()
def create_event(
    event_name: str,
    event_type: str,
    location_id: int,
    start_time: str,
    attendance: int = 1000
) -> Dict[str, Any]:
    """
    Create a new scheduled event.
    
    Args:
        event_name: Name of the event
        event_type: Type of event (e.g., "festival", "sports", "concert")
        location_id: Location ID where the event will take place
        start_time: Start time in ISO format (e.g., "2024-01-15T14:00:00")
        attendance: Expected attendance (default: 1000)
    """
    return social_sim.create_event(event_name, event_type, location_id, start_time, attendance)


@mcp.tool()
def get_simulator_state() -> Dict:
    """
    Get current simulator state including active trends and scheduled events.
    """
    return social_sim.get_state()


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("Starting MCP Social Trends Simulator...")
    state = social_sim.get_state()
    print(f"Active trends: {state['active_trends_count']}")
    print(f"Scheduled events: {state['scheduled_events_count']}")
    mcp.run()
