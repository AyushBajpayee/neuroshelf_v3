"""
MCP Server for Competitor Pricing Simulation
Provides realistic competitor pricing data
"""
import asyncio
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from simulator import competitor_sim

# Initialize MCP Server
mcp = FastMCP("MCP Competitor Pricing Simulator")


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@mcp.tool()
def health_check() -> dict:
    """
    Check competitor simulator health status.
    """
    return {
        "status": "healthy",
        "service": "mcp-competitor-simulator",
        "competitor_count": len(competitor_sim.get_state()["competitors"]),
    }


@mcp.tool()
def get_competitor_prices(sku_id: int, location_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get current prices from all competitors for a SKU.
    
    Args:
        sku_id: The SKU ID to get competitor prices for
        location_id: Optional location ID for location-specific pricing
    """
    return competitor_sim.get_competitor_prices(sku_id, location_id)


@mcp.tool()
def get_competitor_history(sku_id: int, days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Get historical competitor prices for a SKU.
    
    Args:
        sku_id: The SKU ID to get history for
        days_back: Number of days to look back (default: 7)
    """
    return competitor_sim.get_competitor_history(sku_id, days_back)


@mcp.tool()
def trigger_competitor_promo(
    competitor_name: str, 
    sku_id: int, 
    discount_percent: float
) -> Dict[str, Any]:
    """
    Manually trigger a competitor promotion.
    
    Args:
        competitor_name: Name of the competitor
        sku_id: The SKU ID for the promotion
        discount_percent: Discount percentage (0-50)
    """
    return competitor_sim.trigger_competitor_promo(competitor_name, sku_id, discount_percent)


@mcp.tool()
def end_competitor_promo(competitor_name: str, sku_id: int) -> Dict[str, Any]:
    """
    End an active competitor promotion.
    
    Args:
        competitor_name: Name of the competitor
        sku_id: The SKU ID for the promotion to end
    """
    return competitor_sim.end_competitor_promo(competitor_name, sku_id)


@mcp.tool()
def react_to_our_promotion(sku_id: int, our_price: float) -> List[Dict[str, Any]]:
    """
    Simulate competitor reactions to our pricing changes.
    
    Args:
        sku_id: The SKU ID that we changed price for
        our_price: Our new price for the SKU
    """
    return competitor_sim.react_to_our_promotion(sku_id, our_price)


@mcp.tool()
def update_competitor_strategy(competitor_name: str, new_strategy: str) -> Dict[str, Any]:
    """
    Update a competitor's pricing strategy (for testing).
    
    Args:
        competitor_name: Name of the competitor
        new_strategy: New strategy - one of: "aggressive", "premium", "follower"
    """
    return competitor_sim.update_strategy(competitor_name, new_strategy)


@mcp.tool()
def get_simulator_state() -> Dict:
    """
    Get current simulator state including competitors and active promotions.
    """
    return competitor_sim.get_state()


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    # print("Starting MCP Competitor Pricing Simulator...")
    # print(f"Configured competitors: {list(competitor_sim.get_state()['competitors'].keys())}")
    asyncio.run(mcp.run())

