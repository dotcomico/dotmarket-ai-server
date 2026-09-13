"""
Thin OpenAI SDK wrapper. Global/shared: every LLM call in ai-server goes
through chat() here, so the model name, client construction, and (later)
any retry/timeout policy live in exactly one place.

Step 4 scope: prove the API key/SDK work with a plain prompt. Tool-calling
is wired in at Step 5 — this file already accepts a `tools` param so that
step doesn't need to touch this one.

Backend-swappable: LLM_BASE_URL lets this point at any OpenAI-compatible
endpoint instead of OpenAI's own servers — e.g. Ollama's local server
(http://localhost:11434/v1) for free local development. Ollama implements
the same request/response schema (tools, tool_calls, etc.), so no other
code here or in tool_schema.py needs to change; only which server the SDK
talks to and which model name it asks for. Leave LLM_BASE_URL unset to
use real OpenAI.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

load_dotenv()

_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
_BASE_URL = os.environ.get("LLM_BASE_URL") or None
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Builds the OpenAI client on first use rather than at import time, so
    importing this module doesn't crash before OPENAI_API_KEY is set."""
    global _client
    if _client is None:
        # Ollama ignores the key's value but the SDK requires a non-empty
        # string, so OPENAI_API_KEY can be any placeholder when LLM_BASE_URL
        # points at Ollama.
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=_BASE_URL)
    return _client


def chat(
    messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.0
) -> ChatCompletion:
    """Sends messages to the LLM and returns the raw ChatCompletion response.

    Args:
        messages: OpenAI chat message dicts (role/content, etc.).
        tools: OpenAI function-calling tool definitions (see tool_schema.py),
            or None to call without tools.
        temperature: defaults to 0 (deterministic). Tool-calling with small
            local models via Ollama is noticeably flakier at higher
            temperatures — the model can emit its intended call as free-text
            inside `content` instead of the structured `tool_calls` field.
            Low temperature doesn't eliminate that failure mode but cuts it
            a lot, and determinism is what you want for tool selection
            anyway (it's not a creative-writing task).
    """
    kwargs = {"model": _MODEL, "messages": messages, "temperature": temperature}
    if tools is not None:
        kwargs["tools"] = tools
    return _get_client().chat.completions.create(**kwargs)


if __name__ == "__main__":
    response = chat([{"role": "user", "content": "Say hello in exactly 5 words."}])
    print(response.choices[0].message.content)
