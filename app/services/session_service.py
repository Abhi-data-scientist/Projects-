import contextvars
import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from services.redis_client import rdelete, rjson_get, rjson_set

logger = logging.getLogger("session_service")

_CTX_TTL = 7200  # 2 h — in-progress booking
_MAX_HISTORY = 12
_CHAT_HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "chat_history.json"
_history_lock = threading.Lock()
_active_session_token: contextvars.ContextVar[str] = contextvars.ContextVar(
    "active_session_token", default=""
)
_local_context: dict[int, tuple[float, dict]] = {}


# ── Booking context (in-progress booking flow) ────────────────────────────────

def get_booking_context(user_id: int) -> dict:
    cached = rjson_get(f"user:{user_id}:booking_context")
    if cached is not None:
        return cached
    entry = _local_context.get(user_id)
    if entry and entry[0] > time.monotonic():
        return entry[1].copy()
    _local_context.pop(user_id, None)
    return {}


def set_booking_context(user_id: int, ctx: dict):
    rjson_set(f"user:{user_id}:booking_context", ctx, _CTX_TTL)
    _local_context[user_id] = (time.monotonic() + _CTX_TTL, ctx.copy())


def clear_booking_context(user_id: int):
    rdelete(f"user:{user_id}:booking_context")
    _local_context.pop(user_id, None)


# ── File-based chat history ──────────────────────────────────────────────────

def set_chat_session_id(token: str):
    """Set the current request's session without writing its bearer token to disk."""
    _active_session_token.set(token)


def _session_id() -> str:
    token = _active_session_token.get()
    # A fingerprint identifies the session but cannot be reused as an auth token.
    return hashlib.sha256(token.encode()).hexdigest() if token else "unknown"


def _read_history() -> list[dict]:
    if not _CHAT_HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(_CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read chat history file: %s", exc)
        return []


def _write_history(history: list[dict]):
    _CHAT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = _CHAT_HISTORY_FILE.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary_file, _CHAT_HISTORY_FILE)


def append_chat_message(user_id: int, role: str, content: str):
    """Append a message to the JSON list; chat messages are never written to MySQL."""
    message = {
        "user_id": user_id,
        "session_id": _session_id(),
        "role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _history_lock:
        history = _read_history()
        history.append(message)
        _write_history(history)


def get_chat_history(user_id: int, limit: int = _MAX_HISTORY) -> list[dict]:
    """Return the latest messages for one user from the local JSON history file."""
    with _history_lock:
        history = _read_history()
    user_history = [message for message in history if message.get("user_id") == user_id]
    return [
        {"role": message["role"], "content": message["content"]}
        for message in user_history[-limit:]
        if message.get("role") in {"user", "assistant"} and isinstance(message.get("content"), str)
    ]
