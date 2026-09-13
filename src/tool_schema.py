"""
Converts MCP tool definitions into OpenAI's function-calling tool format.

Global/shared: any code in ai-server building a tool list for an OpenAI
`chat()` call goes through this, rather than hand-rolling the conversion
inline. MCP's {name, description, inputSchema} and OpenAI's
{"type": "function", "function": {name, description, parameters}} are
both JSON Schema underneath, so the conversion is close to 1:1 — the only
real work is renaming inputSchema -> parameters and wrapping it.
"""
from typing import Any

from mcp.types import Tool as MCPTool


def mcp_tool_to_openai(tool: MCPTool) -> dict[str, Any]:
    """Converts a single MCP tool definition to an OpenAI tool dict."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


def mcp_tools_to_openai(tools: list[MCPTool]) -> list[dict[str, Any]]:
    """Converts a list of MCP tool definitions to OpenAI tool dicts."""
    return [mcp_tool_to_openai(tool) for tool in tools]
