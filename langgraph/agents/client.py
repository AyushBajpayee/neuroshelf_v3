import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server via stdio"""

        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
        )

        read_stream, write_stream = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        print(
            "\nConnected to server with tools:",
            [tool.name for tool in response.tools],
        )

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python client.py <path_to_server_script>")
    #     sys.exit(1)

    # server_path = sys.argv[1]
    # print(server_path)

    client = MCPClient()
    try:
        await client.connect_to_server(
            "mcp-servers/competitor-simulator/server.py"
        )
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
