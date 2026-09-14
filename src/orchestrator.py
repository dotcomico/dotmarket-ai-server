"""
ask() — the whole MCP <-> ai-server <-> LLM loop in one function.

Global/shared: this is the one place anything in ai-server should go to
ask a question and get a grounded answer back. Generalizes the three
smoke tests (tool_selection, tool_dispatch, grounded_answer) into a loop
that keeps dispatching tool calls until the model is done with them,
handling however many tool_calls come back in a single turn — not just
the first one.

No HTTP API layer, no conversation memory across calls yet — each ask()
call is a fresh, single-turn conversation. Those are explicitly out of
scope per the build plan; this is only the proven MCP/LLM loop.

Prerequisites: same as the smoke tests —
  - mcp-server running (`python -m src.server`, from mcp-server/)
  - Flask backend running (`python -m src.main`, from backend/)
"""
import asyncio
import json
import sys

from src.llm_client import chat
from src.mcp_client import mcp_session
from src.tool_schema import mcp_tools_to_openai

MAX_TOOL_ROUNDS = 5  # guards against a model that never stops calling tools


async def ask(prompt: str) -> str:
    """Sends `prompt` through the MCP tool loop and returns the model's
    final natural-language answer, grounded in real backend data.

    Loops because a single turn can contain multiple tool_calls (e.g. the
    model looking up two different products), and because after seeing
    one round of results the model may legitimately need to call another
    tool before it can answer — MAX_TOOL_ROUNDS caps that so a
    misbehaving model can't loop forever.
    """
    async with mcp_session() as session:
        tools = mcp_tools_to_openai((await session.list_tools()).tools)
        messages = [{"role": "user", "content": prompt}]

        for _ in range(MAX_TOOL_ROUNDS):
            response = chat(messages=messages, tools=tools)
            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            messages.append(message.model_dump(exclude_none=True))

            for call in message.tool_calls:
                args = json.loads(call.function.arguments)
                result = await session.call_tool(call.function.name, args)
                result_text = "\n".join(
                    block.text if hasattr(block, "text") else str(block)
                    for block in result.content
                )
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result_text}
                )

        return "(gave up after too many tool-call rounds without a final answer)"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    prompt = " ".join(sys.argv[1:]) or "What products do you have under $5?"
    try:
        answer = asyncio.run(ask(prompt))
        print(answer)
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        print(
            "Is mcp-server running (python -m src.server, from mcp-server/) "
            "AND the Flask backend running (python -m src.main, from backend/)?",
            file=sys.stderr,
        )
        sys.exit(1)
