"""
Smoke test: dispatch an LLM-chosen tool call against the real mcp-server
tool and print the JSON that comes back from the live Flask backend.

Local: standalone regression check, same family as tool_selection_smoketest
— dispatch here is inlined for the smoke test, but the same
name/arguments -> call_tool(...) flow moves into the orchestrator (Step 8)
so ask() can dispatch whatever tool_calls the model returns, not just this
one hardcoded prompt.

Prerequisites: both must be running —
  - mcp-server: `python -m src.server` (from mcp-server/)
  - Flask backend: `python -m src.main` (from backend/) — mcp-server's
    tools proxy real HTTP requests to it, so get_products here hits real
    product data.
"""
import asyncio
import json
import sys

# Product names/descriptions from the backend can contain emoji; Windows'
# default console codepage can't encode them, so force UTF-8 stdout rather
# than letting print() crash on real data.
sys.stdout.reconfigure(encoding="utf-8")

from src.llm_client import chat
from src.mcp_client import mcp_session
from src.tool_schema import mcp_tools_to_openai

PROMPT = "What products do you have under $5?"


async def main() -> None:
    async with mcp_session() as session:
        result = await session.list_tools()
        tools = mcp_tools_to_openai(result.tools)

        response = chat(
            messages=[{"role": "user", "content": PROMPT}],
            tools=tools,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            print("[WARN] Model returned plain text instead of a tool call — nothing to dispatch:")
            print(message.content)
            return

        call = message.tool_calls[0]
        args = json.loads(call.function.arguments)
        print(f"Dispatching: {call.function.name}({args})\n")

        tool_result = await session.call_tool(call.function.name, args)

    print("Raw result from mcp-server (proxied from the live backend):")
    for block in tool_result.content:
        print(block.text if hasattr(block, "text") else block)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        print(
            "Is mcp-server running (python -m src.server, from mcp-server/) "
            "AND the Flask backend running (python -m src.main, from backend/)?",
            file=sys.stderr,
        )
        sys.exit(1)
