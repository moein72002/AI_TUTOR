from __future__ import annotations

from typing import Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ai_tutor.llm.chain import convert_dict_messages_to_langchain, get_langchain_chat
from ai_tutor.graph.tutor import build_system_prompt
from ai_tutor.services.session_store import ChatMessage, Session, SessionStore
from ai_tutor.services.web_search import is_tavily_configured, tavily_search


class TutorState(TypedDict, total=False):
    messages: List[Dict[str, str]]
    enable_web_search: bool


def node_maybe_search(state: TutorState) -> TutorState:
    if state.get("enable_web_search") and is_tavily_configured():
        try:
            user_last = state["messages"][-1]["content"] if state.get("messages") else ""
            results = tavily_search(user_last, max_results=3)
            if results:
                bullets = "\n".join(
                    [f"- {r['title']}: {r['url']}" for r in results if r.get("title") and r.get("url")]
                )
                augmentation = (
                    "Relevant web findings (use with caution, verify facts):\n" + bullets
                )
                state["messages"].append({"role": "system", "content": augmentation})
        except Exception:
            pass
    return state


def node_call_llm(state: TutorState) -> TutorState:
    chat = get_langchain_chat()
    lc_messages = convert_dict_messages_to_langchain(state["messages"])
    ai_msg = chat.invoke(lc_messages)
    state["messages"].append({"role": "assistant", "content": ai_msg.content})
    return state


class LangTutorGraph:
    def __init__(self, store: Optional[SessionStore] = None) -> None:
        self.store = store or SessionStore()
        self._graph = StateGraph(TutorState)
        self._graph.add_node("maybe_search", node_maybe_search)
        self._graph.add_node("call_llm", node_call_llm)
        self._graph.set_entry_point("maybe_search")
        self._graph.add_edge("maybe_search", "call_llm")
        self._graph.add_edge("call_llm", END)
        self._app = self._graph.compile()

    def start_session(self, subject: str, goal: Optional[str]) -> Session:
        session = self.store.create_session(subject=subject, goal=goal)
        session.messages.append(
            ChatMessage(role="system", content=build_system_prompt(subject, goal))
        )
        # Proactively generate the first assistant message to kick off the lesson
        try:
            chat = get_langchain_chat()
            lc_messages = convert_dict_messages_to_langchain([
                {"role": "system", "content": build_system_prompt(subject, goal)},
                {
                    "role": "user",
                    "content": (
                        "Start the lesson with a brief greeting and a 3-step plan tailored to the subject and goal. "
                        "Ask one quick diagnostic question to gauge current understanding."
                    ),
                },
            ])
            ai_msg = chat.invoke(lc_messages)
            session.messages.append(ChatMessage(role="assistant", content=ai_msg.content))
        except Exception:
            # If the proactive call fails, we still return a valid session
            pass
        self.store.save_session(session)
        return session

    def continue_session(
        self, session_id: str, user_message: str, enable_web_search: bool = False
    ) -> Session:
        session = self.store.load_session(session_id)
        session.messages.append(ChatMessage(role="user", content=user_message))
        state: TutorState = {
            "messages": [{"role": m.role, "content": m.content} for m in session.messages],
            "enable_web_search": enable_web_search,
        }
        # Propagate helpful tracing metadata/tags for LangSmith when enabled via env
        result = self._app.invoke(
            state,
            config={
                "tags": ["ai_tutor", "langgraph"],
                "metadata": {"engine": "langgraph", "subject": session.subject},
            },
        )
        # Sync back the new assistant message
        new_msgs = result["messages"][len(session.messages) :]
        for m in new_msgs:
            session.messages.append(ChatMessage(role=m["role"], content=m["content"]))
        self.store.save_session(session)
        return session


