"""
In-memory session store.

Vanilla-Python and dependency-free by design. Each session holds the
running output of every agent so later agents (and the frontend) can read
prior stages. Swap this module for a SQLite/Redis-backed version later
without touching agent or router code - it's only ever accessed through
the four functions below.
"""
import uuid
from threading import Lock

from app.schemas import SessionState

_sessions: dict[str, SessionState] = {}
_lock = Lock()


def create_session(query: str, tech_hint: str | None) -> SessionState:
    session_id = uuid.uuid4().hex[:12]
    state = SessionState(session_id=session_id, query=query, tech_hint=tech_hint)
    with _lock:
        _sessions[session_id] = state
    return state


def get_session(session_id: str) -> SessionState | None:
    with _lock:
        return _sessions.get(session_id)


def save_session(state: SessionState) -> None:
    with _lock:
        _sessions[state.session_id] = state


def delete_session(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)
