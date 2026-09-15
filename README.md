# Supermarket AI Server

A chatbot/agent service that answers product and category questions grounded
in real backend data. It's the MCP *client* half of the pair with
[`mcp-server`](../mcp-server) (a sibling, separately-git-tracked repo): an
LLM decides which MCP tools to call, `mcp-server` translates those calls into
backend REST requests, and this service turns the result into a natural-
language answer.

## Architecture

```
Frontend chat widget (or curl / any HTTP client)
        │  HTTP POST /chat
        ▼
  src/api.py          — FastAPI endpoint; adapts ask()'s request/response
                         shape to JSON, turns exceptions into a 502
        │
        ▼
  src/orchestrator.py — ask(): the MCP <-> LLM tool-calling loop. Lists
                         mcp-server's tools, sends them to the model,
                         dispatches whatever tool_calls come back, loops
                         until the model returns a final answer (capped by
                         MAX_TOOL_ROUNDS)
        │                              │
        ▼                              ▼
  src/mcp_client.py               src/llm_client.py
  — connects to mcp-server        — thin OpenAI SDK wrapper; swappable to
    over Streamable HTTP            any OpenAI-compatible endpoint (e.g.
    (MCP_SERVER_URL)                Ollama) via LLM_BASE_URL
        │                              │
        ▼                              ▼
  mcp-server (../mcp-server)      OpenAI API, or a local OpenAI-compatible
  — exposes backend tools           server (Ollama, etc.)
        │
        ▼
  Flask backend (../backend) — owns all data, validation, business rules
```

`src/tool_schema.py` converts MCP tool definitions (`{name, description,
inputSchema}`) into OpenAI's function-calling tool format (`{type:
"function", function: {name, description, parameters}}`) — both are JSON
Schema underneath, so the conversion is close to 1:1.

This service has no business logic and no database access of its own — same
principle as `mcp-server`: it only orchestrates the LLM ↔ tool loop.

## Setup

```bash
cd ai-server
python -m venv venv
.\venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | yes | Real OpenAI key, or any placeholder string if `LLM_BASE_URL` points at Ollama (Ollama ignores the value, but the SDK requires a non-empty string) |
| `MCP_SERVER_URL` | no | Default `http://127.0.0.1:8000/mcp` — where `mcp-server` is listening |
| `LLM_BASE_URL` | no | Point at a local OpenAI-compatible server (e.g. Ollama at `http://localhost:11434/v1`) instead of real OpenAI, for free local development |
| `OPENAI_MODEL` | no | Default `gpt-4o-mini`. With Ollama, pick a tool-capable, non-"thinking" model — `qwen2.5:7b` works well; "thinking" models (qwen3.5, gemma4) add 15-20s per call generating chain-of-thought before every answer |
| `AI_SERVER_PORT` | no | Default `8100` — port the FastAPI HTTP endpoint listens on |

## Running

Requires **both** of the following already running:
1. Flask backend — `python -m src.main` from `backend/` → `http://localhost:3000`
2. `mcp-server` — `python -m src.server` from `mcp-server/` → `http://127.0.0.1:8000/mcp`

Then, from `ai-server/`:

```bash
# HTTP API (for the frontend chat widget, or curl)
uvicorn src.api:app --port 8100 --reload
```

```bash
# Or: one-shot CLI query, no HTTP server
python -m src.orchestrator "What products do you have under $5?"
```

### Manual testing

With the backend and `mcp-server` already running, and `src.api` started:

```bash
curl -X POST http://127.0.0.1:8100/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What products do you have under $5?\"}"
```

Expect a JSON `{"reply": "..."}` grounded in real product data — if the
model can't reach `mcp-server` or the backend, you'll get a 502 with an
`error` field instead of a crash.

There are also standalone smoke-test scripts (`src/tool_selection_smoketest.py`,
`src/tool_dispatch_smoketest.py`, `src/grounded_answer_smoketest.py`) that
each verify one step of the MCP/LLM loop in isolation — useful when
debugging a broken link in the chain above without the full HTTP layer.

## Scope

Single-turn only — each `/chat` call is a fresh conversation with no memory
across requests, and no auth. This mirrors `mcp-server`'s current tool
surface, which is read-only product/category lookups with no auth either
(see `mcp-server/README.md`'s "Known gaps" for what's intentionally not
built yet).

## Known issues / improvements

Tracked in [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) and
[`IMPROVEMENT_SUGGESTIONS.md`](IMPROVEMENT_SUGGESTIONS.md) rather than here.
