"""
Thin OpenAI SDK wrapper. Global/shared: every LLM call in ai-server goes
through chat() here, so the model name, client construction, and (later)
any retry/timeout policy live in exactly one place.

Step 4 scope: prove the API key/SDK work with a plain prompt. Tool-calling
is wired in at Step 5 — this file already accepts a `tools` param so that
step doesn't need to touch this one.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

load_dotenv()

_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Builds the OpenAI client on first use rather than at import time, so
    importing this module doesn't crash before OPENAI_API_KEY is set."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def chat(messages: list[dict], tools: list[dict] | None = None) -> ChatCompletion:
    """Sends messages to the LLM and returns the raw ChatCompletion response.

    Args:
        messages: OpenAI chat message dicts (role/content, etc.).
        tools: OpenAI function-calling tool definitions (see tool_schema.py),
            or None to call without tools.
    """
    kwargs = {"model": _MODEL, "messages": messages}
    if tools is not None:
        kwargs["tools"] = tools
    return _get_client().chat.completions.create(**kwargs)


if __name__ == "__main__":
    response = chat([{"role": "user", "content": "Say hello in exactly 5 words."}])
    print(response.choices[0].message.content)
