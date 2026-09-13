"""
MCP client — connects to mcp-server over Streamable HTTP.

mcp-server is a standalone, independently-deployed service (its own
process, its own port) — this client reaches it by URL, the same way it
will later call the OpenAI API by URL. No filesystem coupling between the
two services: ai-server has no knowledge of mcp-server's folder layout,
venv, or how it's started.

Step 2 scope: connect and list tools only. No LLM involved yet — this just
proves ai-server can reach mcp-server before anything else is built on top.

Prerequisite: mcp-server must already be running (`python -m src.server`
from mcp-server/, listening on MCP_SERVER_URL).
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")


@asynccontextmanager
async def mcp_session():
    """Yields a live ClientSession connected to mcp-server over HTTP.

    Global/shared: any code in ai-server that needs to call an MCP tool
    should go through this rather than opening its own connection.
    """
    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def list_tools() -> None:
    """Connects to mcp-server and prints each tool's name, description, and
    input schema. Standalone connectivity check — no LLM involved."""
    async with mcp_session() as session:
        result = await session.list_tools()
        print(f"Connected to {MCP_SERVER_URL}. {len(result.tools)} tool(s) available:\n")
        for tool in result.tools:
            print(f"- {tool.name}")
            print(f"  description: {tool.description}")
            print(f"  inputSchema: {tool.inputSchema}")
            print()


if __name__ == "__main__":
    try:
        asyncio.run(list_tools())
    except Exception as exc:
        print(f"Failed to connect to mcp-server at {MCP_SERVER_URL}: {exc}", file=sys.stderr)
        print("Is mcp-server running? (python -m src.server, from mcp-server/)", file=sys.stderr)
        sys.exit(1)
