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

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.orchestrator import ask

load_dotenv()
# Do we need CORS here? 
app = FastAPI(title="ai-server")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = await ask(request.message)
        return ChatResponse(reply=reply)
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"error": f"Couldn't reach the assistant: {exc}"},
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("AI_SERVER_PORT", 8100))
    uvicorn.run("src.api:app", host="127.0.0.1", port=port, reload=True)
