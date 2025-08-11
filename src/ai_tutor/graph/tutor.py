from __future__ import annotations

from typing import Dict, List, Optional

from ai_tutor.llm.providers import get_llm_provider, is_llm_configured
from ai_tutor.services.session_store import ChatMessage, Session, SessionStore
from ai_tutor.services.web_search import is_tavily_configured, tavily_search


def build_system_prompt(subject: str, goal: Optional[str]) -> str:
    goal_clause = f" The learner's goal is: {goal}." if goal else ""
    return (
        "You are a patient, Socratic AI tutor. Ask guiding questions, break problems into steps, "
        "and adapt to the learner's knowledge. Prefer concise explanations and examples."
        + goal_clause
        + f" You are tutoring the subject: {subject}."
        " Always verify understanding before moving on."
    )


def ensure_system_message(session: Session) -> None:
    if not any(m.role == "system" for m in session.messages):
        session.messages.insert(0, ChatMessage(role="system", content=build_system_prompt(session.subject, session.goal)))


def generate_reply(session: Session, user_message: str, temperature: float = 0.2, enable_web_search: bool = False) -> str:
    if not is_llm_configured():
        raise RuntimeError(
            "LLM is not configured. Set OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL in your environment."
        )
    ensure_system_message(session)
    provider = get_llm_provider()
    messages_payload: List[Dict[str, str]] = [
        {"role": m.role, "content": m.content} for m in session.messages
    ]
    augmented_user = user_message
    if enable_web_search and is_tavily_configured():
        # Attempt a brief search and add a short summary to the user message to give model fresh context
        try:
            results = tavily_search(user_message, max_results=3)
            if results:
                bullets = "\n".join(
                    [f"- {r['title']}: {r['url']}" for r in results if r.get("title") and r.get("url")]
                )
                augmented_user = (
                    f"{user_message}\n\nRelevant web findings (use with caution, verify facts):\n{bullets}"
                )
        except Exception:
            # If online search fails, continue without augmentation
            pass
    messages_payload.append({"role": "user", "content": augmented_user})
    return provider.generate(messages=messages_payload, temperature=temperature)


class TutorGraph:
    """Simple orchestration layer between UI, storage, and LLM provider."""

    def __init__(self, store: Optional[SessionStore] = None) -> None:
        self.store = store or SessionStore()

    def start_session(self, subject: str, goal: Optional[str]) -> Session:
        session = self.store.create_session(subject=subject, goal=goal)
        # Prime system message immediately for persistence
        session.messages.append(
            ChatMessage(role="system", content=build_system_prompt(subject, goal))
        )
        self.store.save_session(session)
        return session

    def continue_session(self, session_id: str, user_message: str, temperature: float = 0.2, enable_web_search: bool = False) -> Session:
        session = self.store.load_session(session_id)
        assistant_reply = generate_reply(
            session=session,
            user_message=user_message,
            temperature=temperature,
            enable_web_search=enable_web_search,
        )
        # Persist user and assistant turns
        session.messages.append(ChatMessage(role="user", content=user_message))
        session.messages.append(ChatMessage(role="assistant", content=assistant_reply))
        self.store.save_session(session)
        return session


