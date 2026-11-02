# 🛒 Dotmarket AI Server

The chat assistant for **[Dotmarket](https://github.com/dotcomico/dotmarket)**, a full-stack supermarket e-commerce app. It answers customer questions about products and categories using real store data, so replies come from the catalog instead of from the model's general knowledge.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![OpenAI compatible](https://img.shields.io/badge/LLM-OpenAI%20%7C%20Ollama-412991)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> [!NOTE]
> This is one of four repos that make up Dotmarket. For the overview, screenshots and full setup, start with the **[main repo](https://github.com/dotcomico/dotmarket)**.

## 💬 How a Question Gets Answered

1. A customer asks, "What products do you have under 5 dollars?"
2. The AI model picks a tool, such as `get_products` with a maximum price.
3. This service calls the tool through the [MCP server](https://github.com/dotcomico/dotmarket-mcp-server), which gets the data from the backend.
4. The result goes back to the model, which may call more tools (5 rounds at most).
5. The model writes the final answer from that data.

## 🏗️ Architecture

```
Frontend chat widget (or curl / any HTTP client)
        │  HTTP POST /chat
        ▼
  src/api.py          FastAPI endpoint. Turns failures into a 502
        │             response instead of a crash.
        ▼
  src/orchestrator.py ask(): the tool-calling loop between the AI model
        │             and the MCP server, capped by MAX_TOOL_ROUNDS.
        │
        ├──────────────────────────────┐
        ▼                              ▼
  src/mcp_client.py               src/llm_client.py
  Connects to mcp-server          Thin OpenAI SDK wrapper. Works with any
  over Streamable HTTP            OpenAI-compatible server through LLM_BASE_URL
        │                              │
        ▼                              ▼
  dotmarket-mcp-server            OpenAI API, or a local server such as Ollama
        │
        ▼
  Dotmarket backend    Owns all data, validation and business rules
```

`src/tool_schema.py` converts MCP tool definitions into OpenAI's function-calling format. Both use JSON Schema, so the conversion is close to 1:1.

This service has no business logic or database access of its own. It only runs the loop between the model and the tools.

## 🚀 Getting Started

**You need:**
- Python 3.11+
- The [backend](https://github.com/dotcomico/dotmarket-server) running at `http://localhost:3000`
- The [MCP server](https://github.com/dotcomico/dotmarket-mcp-server) running at `http://127.0.0.1:8000/mcp`
- An OpenAI API key, or a local [Ollama](https://ollama.com) server for free local use

```bash
git clone https://github.com/dotcomico/dotmarket-ai-server.git ai-server
cd ai-server

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`. To use Ollama instead, see the table below. Then start the server:

```bash
uvicorn src.api:app --port 8100 --reload
```

### Try it

```bash
curl -X POST http://127.0.0.1:8100/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What products do you have under 5 dollars?\"}"
```

You should get `{"reply": "..."}` based on real product data. If the model, `mcp-server` or the backend can't be reached, you get a 502 with an `error` field.

To ask one question without starting the HTTP server:

```bash
python -m src.orchestrator "What products do you have under 5 dollars?"
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Your OpenAI key. With Ollama, use any non-empty text: Ollama ignores it, but the SDK requires a value. |
| `MCP_SERVER_URL` | No | Where `mcp-server` is listening. Default: `http://127.0.0.1:8000/mcp` |
| `LLM_BASE_URL` | No | Address of a local OpenAI-compatible server, such as `http://localhost:11434/v1` for Ollama |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini`. With Ollama, pick a tool-capable model without a "thinking" step. `qwen2.5:7b` works well, while thinking models such as `qwen3.5` and `gemma4` add 15-20 seconds per call. |
| `AI_SERVER_PORT` | No | Port used when starting with `python -m src.api`. Default: `8100` |
| `CHAT_TRACE_ENABLED` | No | Set to `true` in development to record chats. See [Chat tracing](#-chat-tracing). |

## 🔎 Chat Tracing

The chat widget only shows the final reply. To see why the assistant answered the way it did, set `CHAT_TRACE_ENABLED=true` in `.env` and restart. Each conversation then gets its own file, with one JSON line per turn:

```
logs/chats/<conversationId>.jsonl
```

Each line holds the message, the history sent, every tool call with its arguments and result, any injected reminder, the model, the duration, and the final reply or error. A failed turn keeps the rounds that finished before it, and a failed log write only prints a warning.

> [!WARNING]
> Keep this off in production. The files contain what customers type, and nothing limits their size or deletes them.

`logs/` is ignored by git and Docker. When a trace shows a real bug, add it to [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md).

## 🧪 Debugging the Loop

These standalone scripts each check one step of the loop, without the HTTP layer:

| Script | Checks |
|---|---|
| `src/tool_selection_smoketest.py` | The model picks a tool |
| `src/tool_dispatch_smoketest.py` | The chosen tool gets called |
| `src/grounded_answer_smoketest.py` | The final answer uses the tool's data |

[`CHAT_TEST_SCRIPT.md`](CHAT_TEST_SCRIPT.md) has a manual script for testing conversations.

## 📏 Scope

- **Conversations:** multi-turn, with no memory on the server. The client sends earlier messages in `history` on each `/chat` call, and only the `user` and `bot` roles are accepted.
- **Abilities:** product and category questions only. There's no login, and the assistant can't place orders. The [MCP server's limitations](https://github.com/dotcomico/dotmarket-mcp-server#-known-limitations) explain what isn't built yet.
- **Known issues:** tracked in [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) and [`IMPROVEMENT_SUGGESTIONS.md`](IMPROVEMENT_SUGGESTIONS.md).

## 🔗 Related Repos

| Repo | Role |
|---|---|
| [`dotmarket`](https://github.com/dotcomico/dotmarket) | Overview, docs and Docker Compose |
| [`dotmarket-client`](https://github.com/dotcomico/dotmarket-client) | Storefront and admin UI, including the chat widget |
| [`dotmarket-server`](https://github.com/dotcomico/dotmarket-server) | REST API, auth and database |
| [`dotmarket-mcp-server`](https://github.com/dotcomico/dotmarket-mcp-server) | Tools this service calls |

## 📄 License

[MIT](LICENSE)
