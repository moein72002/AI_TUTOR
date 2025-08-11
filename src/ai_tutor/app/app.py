from __future__ import annotations

import os
from typing import List, Optional

import streamlit as st

from ai_tutor.graph.tutor import TutorGraph
from ai_tutor.llm.providers import is_llm_configured
from ai_tutor.services.session_store import ChatMessage, SessionStore
from ai_tutor.services.web_search import is_tavily_configured


def _init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = None  # type: Optional[str]
    if "subject" not in st.session_state:
        st.session_state.subject = "Mathematics"
    if "goal" not in st.session_state:
        st.session_state.goal = ""
if "enable_web_search" not in st.session_state:
    st.session_state.enable_web_search = False


_init_state()

st.set_page_config(page_title="AI Tutor", page_icon="🎓", layout="wide")
st.title("🎓 AI Tutor")

store = SessionStore()
graph = TutorGraph(store=store)

with st.sidebar:
    st.header("Session")
    st.selectbox(
        "Subject",
        options=["Mathematics", "Physics", "Chemistry", "Biology", "History", "Programming"],
        key="subject",
    )
    st.text_input("Learning goal (optional)", key="goal", placeholder="e.g., Understand derivatives")
    search_available = is_tavily_configured()
    st.toggle(
        "Enable web search (Tavily)",
        key="enable_web_search",
        help="Augment answers with brief web findings when available.",
        disabled=not search_available,
    )
    if not search_available:
        st.caption("Set TAVILY_API_KEY in .env to enable web search.")
        if st.session_state.enable_web_search:
            st.session_state.enable_web_search = False

    if st.button("Start new session", type="primary"):
        session = graph.start_session(subject=st.session_state.subject, goal=st.session_state.goal or None)
        st.session_state.session_id = session.session_id

    st.markdown("---")
    st.subheader("History")
    sessions = store.list_sessions()
    if sessions:
        labels = [f"{it['session_id'][:8]} • {it.get('subject','')}" for it in sessions]
        choice = st.selectbox("Load session", options=["-"] + labels, index=0)
        if choice != "-":
            idx = labels.index(choice)
            st.session_state.session_id = sessions[idx]["session_id"]
    else:
        st.caption("No saved sessions yet.")


if not is_llm_configured():
    st.warning(
        "LLM is not configured. Set OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL in your .env and restart the container.",
        icon="⚠️",
    )


def render_chat(session_id: str) -> None:
    session = store.load_session(session_id)
    for msg in session.messages:
        if msg.role == "system":
            continue
        with st.chat_message(msg.role):
            st.markdown(msg.content)

    if prompt := st.chat_input("Ask a question or describe a problem..."):
        with st.spinner("Thinking..."):
            try:
                updated = graph.continue_session(
                    session_id=session_id,
                    user_message=prompt,
                    enable_web_search=st.session_state.enable_web_search,
                )
            except Exception as exc:  # surface error to user in UI but do not crash
                st.error(str(exc))
                return
        # Render the last two turns (user + assistant)
        with st.chat_message("user"):
            st.markdown(prompt)
        last = updated.messages[-1] if updated.messages else None
        if last and last.role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(last.content)


if st.session_state.session_id:
    render_chat(st.session_state.session_id)
else:
    st.info("Start a new session from the sidebar to begin.")


