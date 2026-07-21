from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, TypedDict

from app.config.settings import settings


class ConversationTurn(TypedDict):
    role: str  # "user" | "assistant"
    content: str
    timestamp: str


@dataclass(frozen=True)
class MemorySnapshot:
    session_id: str
    turns: List[ConversationTurn]


# Max sessions to keep in memory before evicting the oldest
MAX_SESSIONS = 1000

# Evict sessions idle longer than this many seconds (30 minutes)
SESSION_TTL_SECONDS = 1800

# How often the cleanup thread runs (5 minutes)
CLEANUP_INTERVAL_SECONDS = 300


class ConversationMemoryService:
    """In-memory conversation memory with bounded session count and TTL eviction.

    Notes:
    - Thread-safe for concurrent requests within a single process.
    - Old sessions are periodically purged to prevent memory leaks.
    - For high-scale production, swap with Redis/DB.
    """

    def __init__(self, *, max_turns: int = 12) -> None:
        self._max_turns = max_turns
        self._lock = threading.RLock()
        self._sessions: Dict[str, List[ConversationTurn]] = {}
        # Track last access time per session (unix timestamp)
        self._last_access: Dict[str, float] = {}

        # Start background cleanup daemon thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="conv-memory-cleanup",
            daemon=True,
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        """Periodically evict sessions that are too old or exceed the max count."""
        while True:
            time.sleep(CLEANUP_INTERVAL_SECONDS)
            try:
                self._evict_stale_sessions()
            except Exception:
                pass  # Prevent cleanup crash from affecting the main process

    def _evict_stale_sessions(self) -> None:
        """Evict sessions that have been idle beyond TTL, and trim to max count."""
        now = time.time()
        cutoff = now - SESSION_TTL_SECONDS
        with self._lock:
            # Remove stale sessions by TTL
            stale_ids = [
                sid for sid, last_ts in self._last_access.items()
                if last_ts < cutoff
            ]
            for sid in stale_ids:
                self._sessions.pop(sid, None)
                self._last_access.pop(sid, None)

            # If still over MAX_SESSIONS, evict oldest by last access
            if len(self._sessions) > MAX_SESSIONS:
                sorted_ids = sorted(
                    self._last_access.keys(),
                    key=lambda sid: self._last_access[sid],
                )
                excess = len(self._sessions) - MAX_SESSIONS
                for sid in sorted_ids[:excess]:
                    self._sessions.pop(sid, None)
                    self._last_access.pop(sid, None)

    def _touch(self, session_id: str) -> None:
        """Mark session as recently accessed."""
        self._last_access[session_id] = time.time()

    def new_session_id(self) -> str:
        return str(uuid.uuid4())

    def get(self, session_id: str) -> List[ConversationTurn]:
        with self._lock:
            self._touch(session_id)
            turns = self._sessions.get(session_id, [])
            # Return a copy to avoid accidental mutation.
            return list(turns)

    def append_user_assistant_turns(
        self,
        *,
        session_id: str,
        user_content: str,
        assistant_content: str,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        timestamp_now = time.time()
        user_turn: ConversationTurn = {
            "role": "user",
            "content": user_content,
            "timestamp": now,
        }
        assistant_turn: ConversationTurn = {
            "role": "assistant",
            "content": assistant_content,
            "timestamp": now,
        }

        with self._lock:
            self._touch(session_id)
            if session_id not in self._sessions:
                # Evict oldest if at capacity before adding new session
                if len(self._sessions) >= MAX_SESSIONS:
                    oldest_id = min(
                        self._last_access.keys(),
                        key=lambda sid: self._last_access[sid],
                    )
                    self._sessions.pop(oldest_id, None)
                    self._last_access.pop(oldest_id, None)
                self._sessions[session_id] = []

            self._sessions[session_id].append(user_turn)
            self._sessions[session_id].append(assistant_turn)

            # Enforce max turns (turns are user+assistant pairs, so count entries).
            if self._max_turns > 0 and len(self._sessions[session_id]) > self._max_turns:
                self._sessions[session_id] = self._sessions[session_id][-self._max_turns :]

            return len(self._sessions[session_id])

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._last_access.pop(session_id, None)

    def snapshot(self, session_id: str) -> MemorySnapshot:
        return MemorySnapshot(session_id=session_id, turns=self.get(session_id))
