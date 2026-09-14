"""
Smoke test: full round trip — LLM picks a tool, we dispatch it for real,
and the LLM turns the real result into a natural-language answer.

Local: standalone regression check. The message-list bookkeeping here
(assistant tool_calls message -> tool-role result message -> second
chat() call) is exactly what ask() (Step 8) generalizes into a loop that
also handles multiple tool_calls in one turn.

Prerequisites: same as tool_dispatch_smoketest —
  - mcp-server running (`python -m src.server`, from mcp-server/)
  - Flask backend running (`python -m src.main`, from backend/)
"""
import asyncio
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from src.llm_client import chat
from src.mcp_client import mcp_session
from src.tool_schema import mcp_tools_to_openai

PROMPT = "What products do you have under $5?"


async def main() -> None:
    async with mcp_session() as session:
        result = await session.list_tools()
        tools = mcp_tools_to_openai(result.tools)

        messages = [{"role": "user", "content": PROMPT}]

        response = chat(messages=messages, tools=tools)
        message = response.choices[0].message

        if not message.tool_calls:
            print("[WARN] Model returned plain text instead of a tool call — nothing to dispatch:")
            print(message.content)
            return

        call = message.tool_calls[0]
        args = json.loads(call.function.arguments)
        print(f"Dispatching: {call.function.name}({args})\n")

        tool_result = await session.call_tool(call.function.name, args)
        result_text = "\n".join(
            block.text if hasattr(block, "text") else str(block) for block in tool_result.content
        )

    # Append the assistant's tool-call turn, then the tool's result as a
    # `tool`-role message (tool_call_id ties it back to the specific call
    # the model made), and ask again — this time it has real data to work
    # with instead of just the tool list.
    messages.append(message.model_dump(exclude_none=True))
    messages.append(
        {
            "role": "tool",
            "tool_call_id": call.id,
            "content": result_text,
        }
    )

    final = chat(messages=messages, tools=tools)
    answer = final.choices[0].message.content

    print("Final grounded answer:")
    print(answer)


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
