"""
Smoke test: confirm the LLM decides to use an MCP tool when given a prompt
that needs one, without actually dispatching the call.

Local: this is a standalone regression check, not a reusable module — tool
dispatch and the full chat loop live in their own module (orchestrator.py)
once built.

Prerequisite: mcp-server must be running (`python -m src.server` from
mcp-server/) so list_tools() can fetch the tool definitions. The Flask
backend does NOT need to be running — no tool is actually dispatched here,
only offered to the LLM.
"""
import asyncio
import sys

from src.llm_client import chat
from src.mcp_client import mcp_session
from src.tool_schema import mcp_tools_to_openai

PROMPT = "What products do you have under $5?"


async def main() -> None:
    async with mcp_session() as session:
        result = await session.list_tools()
        tools = mcp_tools_to_openai(result.tools)

    print(f"Offering {len(tools)} tool(s) to the model: {[t['function']['name'] for t in tools]}\n")

    response = chat(
        messages=[{"role": "user", "content": PROMPT}],
        tools=tools,
    )

    message = response.choices[0].message
    print("Raw response message:")
    print(message.model_dump_json(indent=2))

    if message.tool_calls:
        print(f"\n[OK] Model chose to call {len(message.tool_calls)} tool(s):")
        for call in message.tool_calls:
            print(f"  - {call.function.name}({call.function.arguments})")
    else:
        print("\n[WARN] Model returned plain text instead of a tool call:")
        print(message.content)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        print("Is mcp-server running? (python -m src.server, from mcp-server/)", file=sys.stderr)
        sys.exit(1)
