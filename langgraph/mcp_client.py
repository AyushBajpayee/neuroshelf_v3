"""
MCP Client for interacting with MCP servers
"""

import httpx
from typing import Dict, Any, Optional
import config


class MCPClient:
    def __init__(self):
        self.servers = config.MCP_SERVERS
        self.client = httpx.Client(timeout=30.0)

    def call_tool(
        self, server_name: str, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on an MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Unknown MCP server: {server_name}")

        url = f"{self.servers[server_name]}/tool"
        payload = {"tool_name": tool_name, "parameters": parameters}

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            if not result.get("success"):
                raise Exception(f"Tool call failed: {result.get('error')}")

            return result.get("data")

        except httpx.HTTPError as e:
            raise Exception(f"MCP server error: {str(e)}")

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Global MCP client instance
mcp_client = MCPClient()
