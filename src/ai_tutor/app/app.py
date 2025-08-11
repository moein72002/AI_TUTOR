from __future__ import annotations

import os
from typing import List, Optional

import streamlit as st
from dotenv import load_dotenv

from ai_tutor.graph.lang_tutor import LangTutorGraph
from ai_tutor.llm.providers import is_llm_configured
from ai_tutor.services.session_store import ChatMessage, SessionStore
from ai_tutor.services.web_search import is_tavily_configured
from ai_tutor.services.quiz import generate_mcq_quiz
from ai_tutor.services.quiz_store import QuizResult, QuizStore
from ai_tutor.services.remediation import generate_remediation


def _init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = None  # type: Optional[str]
    if "subject_choice" not in st.session_state:
        st.session_state.subject_choice = "Mathematics"
    if "subject_custom" not in st.session_state:
        st.session_state.subject_custom = ""
    if "goal" not in st.session_state:
        st.session_state.goal = ""
if "enable_web_search" not in st.session_state:
    st.session_state.enable_web_search = False
    # quiz topic is chosen at quiz time; no need to preset in sidebar
    if "prev_session_id" not in st.session_state:
        st.session_state.prev_session_id = None


def _reset_quiz_ui_state() -> None:
    # Clear quiz widgets and cached quiz when switching sessions or starting new
    for key in list(st.session_state.keys()):
        key_str = str(key)
        if key_str.startswith("quiz_q_") or (key_str.startswith("quiz_") and "_q_" in key_str):
            try:
                del st.session_state[key]
            except Exception:
                pass
    st.session_state.pop("active_quiz_id", None)
    st.session_state.pop("active_quiz", None)


load_dotenv()  # load .env for local runs (Docker uses env_file)
_init_state()

st.set_page_config(page_title="AI Tutor", page_icon="🎓", layout="wide")
st.title("🎓 AI Tutor")

store = SessionStore()
lang_graph = LangTutorGraph(store=store)
quiz_store = QuizStore()

with st.sidebar:
    st.header("Session")
    popular = ["Mathematics", "Physics", "Chemistry", "Biology", "History", "Programming"]
    choices = ["Write your subject choice"] + popular
    st.selectbox("Subject", options=choices, key="subject_choice")
    if st.session_state.subject_choice == "Write your subject choice":
        st.text_input("Write your subject", key="subject_custom", placeholder="e.g., Linear Algebra")
    st.text_input("Learning goal (optional)", key="goal", placeholder="e.g., Understand derivatives")
    search_available = is_tavily_configured()
    st.toggle(
        "Enable web search",
        key="enable_web_search",
        help="Augment answers with brief web findings when available.",
        disabled=not search_available,
    )
    if not search_available:
        st.caption("Set TAVILY_API_KEY in .env to enable web search.")
        if st.session_state.enable_web_search:
            st.session_state.enable_web_search = False

    if st.button("Start new session", type="primary"):
        current_subject = (
            st.session_state.subject_custom
            if st.session_state.subject_choice == "Write your subject choice"
            else st.session_state.subject_choice
        )
        # Prevent duplicate sessions with same subject and goal
        existing = store.find_session_by_subject_goal(current_subject, st.session_state.goal or None)
        if existing:
            st.info("A session with the same subject and goal already exists. Loading it instead.")
            st.session_state.session_id = existing
            st.session_state.prev_session_id = existing
        else:
            session = lang_graph.start_session(subject=current_subject, goal=st.session_state.goal or None)
            # Reset quiz state when starting a new session
            _reset_quiz_ui_state()
            st.session_state.session_id = session.session_id
            st.session_state.prev_session_id = session.session_id
        # Reset quiz state when starting a new session
        _reset_quiz_ui_state()
        st.session_state.session_id = session.session_id
        st.session_state.prev_session_id = session.session_id

    st.markdown("---")
    st.subheader("History")
    sessions = store.list_sessions()
    if sessions:
        labels = [
            f"{it.get('subject','')}: {it.get('goal','') or '-'}" for it in sessions
        ]
        choice = st.selectbox("Load session", options=["-"] + labels, index=0)
        if choice != "-":
            idx = labels.index(choice)
            selected_id = sessions[idx]["session_id"]
            # Load selected session
            if selected_id != st.session_state.session_id:
                _reset_quiz_ui_state()
            st.session_state.session_id = selected_id
            st.session_state.prev_session_id = selected_id

            # Delete button below the selector
            if st.button("Delete this session", type="secondary"):
                if store.delete_session(selected_id):
                    st.success("Session deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete session.")
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
                updated = lang_graph.continue_session(
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
    st.markdown("---")
    with st.expander("Generate MCQ quiz"):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            current_subject = (
                st.session_state.subject_custom
                if st.session_state.subject_choice == "Write your subject choice"
                else st.session_state.subject_choice
            )
            topic = current_subject
            st.text_input("Topic", value=topic, key="quiz_topic")
        with col2:
            num = st.number_input("Questions", min_value=3, max_value=10, value=5, step=1, key="quiz_num")
        with col3:
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1, key="quiz_difficulty")

        # Create a new quiz
        if st.button("Create quiz", type="primary"):
            with st.spinner("Generating quiz..."):
                try:
                    session = store.load_session(st.session_state.session_id)
                    quiz = generate_mcq_quiz(
                        subject=session.subject,
                        topic=st.session_state.quiz_topic,
                        conversation_messages=[{"role": m.role, "content": m.content} for m in session.messages],
                        num_questions=int(st.session_state.quiz_num),
                        difficulty=st.session_state.quiz_difficulty,
                    )
                except Exception as exc:
                    st.error(str(exc))
                else:
                    payload = quiz.model_dump()
                    # persist quiz JSON for review later and keep in session for rerender
                    quiz_store.save_quiz(
                        session_id=session.session_id,
                        quiz_id=quiz.quiz_id,
                        payload=payload,
                    )
                    st.session_state["active_quiz_id"] = quiz.quiz_id
                    st.session_state["active_quiz"] = payload
                    # Inform user if topic was ignored
                    meta = payload.get("meta") if isinstance(payload, dict) else None
                    if meta and not meta.get("topic_used", True):
                        reason = meta.get("ignored_reason") or "The topic appeared irrelevant to the session context."
                        st.warning(f"The quiz topic was ignored: {reason}")

        # Render active quiz (persisted across reruns)
        active_quiz = st.session_state.get("active_quiz")
        if not active_quiz and st.session_state.get("active_quiz_id"):
            # Attempt to load from disk if not in session
            try:
                session = store.load_session(st.session_state.session_id)
                active_quiz = quiz_store.load_quiz(session_id=session.session_id, quiz_id=st.session_state["active_quiz_id"])  # type: ignore[index]
                st.session_state["active_quiz"] = active_quiz
            except Exception:
                active_quiz = None

        if active_quiz:
            for idx, q in enumerate(active_quiz.get("questions", []), start=1):
                st.subheader(f"Q{idx}. {q['question']}")
                options = q.get("options", [])
                widget_key = f"quiz_{st.session_state.session_id}_q_{idx}"
                choice = st.radio(
                    f"Select answer for Q{idx}", options, index=None, key=widget_key, horizontal=False
                )
                if choice is not None:
                    sel_index = options.index(choice)
                    if sel_index == q.get("correct_index", -1):
                        st.success("Correct! " + q.get("explanation", ""))
                    else:
                        st.error(
                            f"Incorrect. Correct answer: {options[q.get('correct_index', 0)]}\n\n{q.get('explanation','')}"
                        )
            # Scoring (computed on demand)
            if st.button("Submit answers", type="secondary"):
                total = len(active_quiz.get("questions", []))
                correct = 0
                selected_indices: list[int] = []
                for idx, q in enumerate(active_quiz.get("questions", []), start=1):
                    selected = st.session_state.get(f"quiz_{st.session_state.session_id}_q_{idx}")
                    options = q.get("options", [])
                    chosen_index = options.index(selected) if (selected is not None and selected in options) else -1
                    selected_indices.append(chosen_index)
                    if chosen_index != -1 and chosen_index == q.get("correct_index", -1):
                        correct += 1
                st.info(f"Score: {correct} / {total}")
                try:
                    session = store.load_session(st.session_state.session_id)
                    incorrect = [i for i, chosen in enumerate(selected_indices) if chosen == -1 or chosen != active_quiz["questions"][i].get("correct_index", -1)]
                    quiz_store.save_result(
                        QuizResult(
                            session_id=session.session_id,
                            quiz_id=active_quiz.get("quiz_id", "unknown"),
                            topic=active_quiz.get("topic", ""),
                            total_questions=total,
                            correct_answers=correct,
                            selected_indices=selected_indices,
                            incorrect_indices=incorrect,
                        )
                    )
                except Exception:
                    pass

            if st.button("Generate custom lesson", type="primary"):
                try:
                    session = store.load_session(st.session_state.session_id)
                    # Load latest result for this active quiz if available
                    result_files = quiz_store.list_results(session_id=session.session_id)
                    latest = None
                    for r in reversed(result_files):
                        if r.get("quiz_id") == active_quiz.get("quiz_id"):
                            latest = r
                            break
                    incorrect = latest.get("incorrect_indices", []) if latest else []
                    if not incorrect:
                        st.info("No incorrect answers recorded yet. Submit answers first.")
                    else:
                        lesson = generate_remediation(
                            subject=session.subject,
                            topic=active_quiz.get("topic", ""),
                            quiz=active_quiz,
                            incorrect_indices=incorrect,
                        )
                        st.markdown("### Personalized lesson")
                        st.markdown(lesson)
                except Exception as exc:
                    st.error(str(exc))

    st.markdown("---")
    with st.expander("Past quiz results"):
        results = quiz_store.list_results(session_id=st.session_state.session_id)
        if not results:
            st.caption("No quiz results yet.")
        else:
            for r in results:
                st.write(f"Session {r['session_id'][:8]}, Quiz {r['quiz_id'][:8]} • {r['topic']} — {r['correct_answers']}/{r['total_questions']}")
else:
    st.info("Start a new session from the sidebar to begin.")


