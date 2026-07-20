from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, TypedDict


class ConversationTurn(TypedDict):
    role: str  # "user" | "assistant"
    content: str
    timestamp: str


@dataclass(frozen=True)
class MemorySnapshot:
    session_id: str
    turns: List[ConversationTurn]


class ConversationMemoryService:
    """In-memory conversation memory.

    Notes:
    - This is process-local (suitable for dev). For production, swap with Redis/DB.
    - Thread-safe for concurrent requests within a single process.
    """

    def __init__(self, *, max_turns: int = 12) -> None:
        self._max_turns = max_turns
        self._lock = threading.RLock()
        self._sessions: Dict[str, List[ConversationTurn]] = {}

    def new_session_id(self) -> str:
        return str(uuid.uuid4())

    def get(self, session_id: str) -> List[ConversationTurn]:
        with self._lock:
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
            if session_id not in self._sessions:
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

    def snapshot(self, session_id: str) -> MemorySnapshot:
        return MemorySnapshot(session_id=session_id, turns=self.get(session_id))

