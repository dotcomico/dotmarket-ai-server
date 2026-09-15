"""
ask() — the whole MCP <-> ai-server <-> LLM loop in one function.

Global/shared: this is the one place anything in ai-server should go to
ask a question and get a grounded answer back. Generalizes the three
smoke tests (tool_selection, tool_dispatch, grounded_answer) into a loop
that keeps dispatching tool calls until the model is done with them,
handling however many tool_calls come back in a single turn — not just
the first one.

No HTTP API layer here, but callers can now pass in prior conversation
turns: ask() accepts a `history` of {role, text} turns (the frontend's
display-message vocabulary) and seeds the LLM's message list with a
trimmed window of that history before the new prompt. There's still no
persistence — the caller (api.py) is responsible for keeping and
resending history across calls; ask() itself remains stateless between
invocations.

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

# How much prior conversation to feed back to the model. Counted in
# individual history messages (not exchanges), so 10 = the last 5
# user/bot exchanges. Trimming is by message count, not token budget —
# a token-budget-aware version is deferred, not implemented here.
MAX_HISTORY_MESSAGES = 10

SYSTEM_PROMPT = (
    "You are the Dotmarket shopping assistant. Answer only using the tools "
    "available to you; don't invent prices, stock, or product details."
)

# Frontend message roles -> OpenAI chat roles.
_ROLE_MAP = {"user": "user", "bot": "assistant"}


def _build_seed_messages(prompt: str, history: list[dict] | None) -> list[dict]:
    """Converts the frontend's {role, text} history into OpenAI role/content
    messages, trimmed to the last MAX_HISTORY_MESSAGES turns, and appends the
    new user prompt after a system message establishing scope."""
    trimmed = (history or [])[-MAX_HISTORY_MESSAGES:]
    history_messages = [
        {"role": _ROLE_MAP.get(turn["role"], turn["role"]), "content": turn["text"]}
        for turn in trimmed
    ]
    return (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history_messages
        + [{"role": "user", "content": prompt}]
    )


async def ask(prompt: str, history: list[dict] | None = None) -> str:
    """Sends `prompt` (plus any prior `history`) through the MCP tool loop
    and returns the model's final natural-language answer, grounded in real
    backend data.

    `history` is a list of {role, text} turns in the frontend's vocabulary
    (role is "user" or "bot"); it's trimmed to the last
    MAX_HISTORY_MESSAGES messages and converted to OpenAI role/content
    messages before the new prompt. Empty/None history behaves exactly like
    a fresh, single-turn conversation.

    Loops because a single turn can contain multiple tool_calls (e.g. the
    model looking up two different products), and because after seeing
    one round of results the model may legitimately need to call another
    tool before it can answer — MAX_TOOL_ROUNDS caps that so a
    misbehaving model can't loop forever.
    """
    async with mcp_session() as session:
        tools = mcp_tools_to_openai((await session.list_tools()).tools)
        messages = _build_seed_messages(prompt, history)

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
