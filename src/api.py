"""
Thin HTTP layer over orchestrator.ask() — the only reason this file exists
is to give the frontend chat widget an HTTP endpoint to call. No new logic
lives here; it just adapts ask()'s request/response shape to JSON and turns
exceptions (mcp-server down, backend down, model failure) into a proper
error response instead of a crash.

Global/shared: this is the one HTTP entrypoint ai-server exposes. Run with
`uvicorn src.api:app --port <AI_SERVER_PORT>` from ai-server/.
"""
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.chat_trace import ChatTrace, is_enabled as chat_trace_enabled
from src.orchestrator import ask

load_dotenv()
# Do we need CORS here? 
app = FastAPI(title="ai-server")


class HistoryTurn(BaseModel):
    role: Literal["user", "bot"]
    text: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryTurn] = []
    # Becomes a filename in chat_trace.py, so the pattern also blocks path traversal.
    conversationId: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{1,64}$")


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    history = [turn.model_dump() for turn in request.history]
    trace = (
        ChatTrace(request.conversationId, request.message, history)
        if chat_trace_enabled()
        else None
    )
    try:
        reply = await ask(request.message, history, trace)
        if trace:
            trace.reply = reply
        return ChatResponse(reply=reply)
    except Exception as exc:
        if trace:
            trace.error = str(exc)
        return JSONResponse(
            status_code=502,
            content={"error": f"Couldn't reach the assistant: {exc}"},
        )
    finally:
        if trace:
            trace.write()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("AI_SERVER_PORT", 8100))
    uvicorn.run("src.api:app", host="127.0.0.1", port=port, reload=True)
