"""
Dev-only record of what happened during one /chat turn: the tool calls and
results the web chat never shows, written as one JSON line per turn to
logs/chats/<conversationId>.jsonl so a bad conversation can be investigated
later.

Local to ai-server. Off unless CHAT_TRACE_ENABLED=true, because the files
hold whatever customers type. Writing is best-effort: a logging failure
must never cost the customer their reply.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

TRACE_DIR = Path(__file__).resolve().parent.parent / "logs" / "chats"
NO_ID_FILENAME = "no-id"


def is_enabled() -> bool:
    return os.environ.get("CHAT_TRACE_ENABLED", "").strip().lower() == "true"


class ChatTrace:
    """Collects one turn in place, so a crash mid-loop still keeps every
    round that finished before it."""

    def __init__(self, conversation_id: str | None, message: str, history: list[dict]):
        self.conversation_id = conversation_id
        self.message = message
        self.history = history
        self.model: str | None = None
        self.rounds: list[dict] = []
        self.reply: str | None = None
        self.error: str | None = None
        self._started_at = time.perf_counter()

    def start_round(self, model: str, assistant_text: str | None) -> dict:
        self.model = model
        round_entry = {
            "assistantText": assistant_text,
            "toolCalls": [],
            "reminderInjected": False,
        }
        self.rounds.append(round_entry)
        return round_entry

    def to_record(self) -> dict:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "conversationId": self.conversation_id,
            "model": self.model,
            "durationMs": round((time.perf_counter() - self._started_at) * 1000),
            "message": self.message,
            "history": self.history,
            "rounds": self.rounds,
            "reply": self.reply,
            "error": self.error,
        }

    def write(self) -> None:
        try:
            TRACE_DIR.mkdir(parents=True, exist_ok=True)
            path = TRACE_DIR / f"{self.conversation_id or NO_ID_FILENAME}.jsonl"
            with path.open("a", encoding="utf-8") as trace_file:
                trace_file.write(json.dumps(self.to_record(), ensure_ascii=False) + "\n")
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("Couldn't write chat trace: %s", exc)
