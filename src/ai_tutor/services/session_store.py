from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional


Role = Literal["system", "user", "assistant"]


@dataclass
class ChatMessage:
    role: Role
    content: str


@dataclass
class Session:
    session_id: str
    subject: str
    goal: Optional[str]
    messages: List[ChatMessage]
    language: str = "en"


class SessionStore:
    """Persist sessions as JSON files under a base directory.

    Ensures all state is JSON-serializable as required by project rules.
    """

    def __init__(self, base_dir: Path | str = Path("data")) -> None:
        self.base_dir: Path = Path(base_dir)
        self.sessions_dir: Path = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def create_session(self, subject: str, goal: Optional[str], language: str = "en") -> Session:
        session_id = uuid.uuid4().hex
        session = Session(session_id=session_id, subject=subject, goal=goal, messages=[], language=language)
        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> Session:
        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        messages = [ChatMessage(**m) for m in raw["messages"]]
        return Session(
            session_id=raw["session_id"],
            subject=raw.get("subject", ""),
            goal=raw.get("goal"),
            messages=messages,
            language=raw.get("language", "en"),
        )

    def save_session(self, session: Session) -> None:
        path = self._session_path(session.session_id)
        payload = {
            "session_id": session.session_id,
            "subject": session.subject,
            "goal": session.goal,
            "language": getattr(session, "language", "en"),
            "messages": [
                {"role": m.role, "content": m.content} for m in session.messages
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def append_message(self, session_id: str, message: ChatMessage) -> Session:
        session = self.load_session(session_id)
        session.messages.append(message)
        self.save_session(session)
        return session

    def list_sessions(self) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        for file in sorted(self.sessions_dir.glob("*.json")):
            try:
                raw = json.loads(file.read_text(encoding="utf-8"))
            except Exception:
                continue
            items.append(
                {
                    "session_id": raw.get("session_id", file.stem),
                    "subject": raw.get("subject", ""),
                    "goal": raw.get("goal", ""),
                }
            )
        return items

    def delete_session(self, session_id: str) -> bool:
        path = self._session_path(session_id)
        if not path.exists():
            return False
        try:
            path.unlink()
            return True
        except Exception:
            return False

    def find_session_by_subject_goal(self, subject: str, goal: Optional[str]) -> Optional[str]:
        """Return an existing session_id if one matches the exact subject and goal."""
        normalized_goal = goal or ""
        for info in self.list_sessions():
            if info.get("subject", "") == subject and (info.get("goal", "") or "") == normalized_goal:
                return info.get("session_id")
        return None


