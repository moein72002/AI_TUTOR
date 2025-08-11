from pathlib import Path

from ai_tutor.services.session_store import ChatMessage, SessionStore


def test_create_and_persist_session(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path)
    session = store.create_session(subject="Math", goal="Practice algebra")
    assert session.session_id
    assert session.subject == "Math"

    # Append a message and reload
    store.append_message(session.session_id, ChatMessage(role="user", content="What is x if 2x=10?"))
    loaded = store.load_session(session.session_id)
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content.startswith("What is x")


def test_list_sessions(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path)
    s1 = store.create_session(subject="Physics", goal=None)
    s2 = store.create_session(subject="History", goal="WWII overview")
    items = store.list_sessions()
    session_ids = {it["session_id"] for it in items}
    assert s1.session_id in session_ids and s2.session_id in session_ids


