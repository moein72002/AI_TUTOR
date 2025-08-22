from __future__ import annotations

import os
from typing import List, Optional
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Ensure project src/ is on sys.path for local runs without PYTHONPATH
_SRC_DIR = Path(__file__).resolve().parents[2]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from ai_tutor.graph.lang_tutor import LangTutorGraph
from ai_tutor.llm.providers import is_llm_configured
from ai_tutor.services.session_store import ChatMessage, SessionStore
from ai_tutor.services.web_search import is_tavily_configured
from ai_tutor.services.quiz import generate_mcq_quiz
from ai_tutor.services.quiz_store import QuizResult, QuizStore
from ai_tutor.services.remediation import generate_remediation
from ai_tutor.app.i18n import t, get_lang_code, popular_subjects_for_lang, difficulty_display_and_map
from ai_tutor.services.voice import ensure_wav_mono_16k, transcribe_wav_to_text


def _init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = None  # type: Optional[str]
    if "subject_choice" not in st.session_state:
        st.session_state.subject_choice = "Mathematics"
    if "subject_custom" not in st.session_state:
        st.session_state.subject_custom = ""
    if "language" not in st.session_state:
        # Store the UI selection label; map to code via get_lang_code when needed
        st.session_state.language = "English"
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

store = SessionStore()
lang_graph = LangTutorGraph(store=store)
quiz_store = QuizStore()

with st.sidebar:
    # Language selector first, so the rest of the UI reflects the latest choice in the same rerun
    st.selectbox("Language / زبان", options=["English", "فارسی"], key="language")
    lang_code = get_lang_code(st.session_state.language)
    # Direction-aware styling: only affect textual content; leave widgets/buttons LTR
    if lang_code == "fa":
        st.markdown(
            """
            <style>
            /* Make text RTL */
            h1, h2, h3, .stMarkdown, .stCaption, .stSubheader, .stHeader, [data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; }
            /* Make widget labels RTL (keep controls LTR) */
            [data-testid="stWidgetLabel"] { direction: rtl; text-align: right; }
            /* Keep interactive widgets LTR */
            [data-testid="stSwitch"], [data-testid="stSelectbox"], [data-testid="stNumberInput"], [data-testid="stTextInput"], [data-testid="stButton"], [data-testid="stRadio"], [data-testid="stExpander"], [data-testid="stFileUploader"] { direction: ltr; text-align: left; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            h1, h2, h3, .stMarkdown, .stCaption, .stSubheader, .stHeader, [data-testid="stMarkdownContainer"] { direction: ltr; text-align: left; }
            </style>
            """,
            unsafe_allow_html=True,
        )

    st.header(t(lang_code, "session"))
    popular = popular_subjects_for_lang(lang_code)
    custom_option = t(lang_code, "subject_custom_option")
    choices = [custom_option] + popular
    st.selectbox(t(lang_code, "subject"), options=choices, key="subject_choice")
    if st.session_state.subject_choice == custom_option:
        st.text_input(t(lang_code, "subject_custom_option"), key="subject_custom", placeholder=t(lang_code, "subject_custom_placeholder"))
    st.text_input(t(lang_code, "learning_goal_optional"), key="goal", placeholder="e.g., Understand derivatives" if lang_code=="en" else "مثلاً: مشتق را بفهمم")
    search_available = is_tavily_configured()
    st.toggle(
        t(lang_code, "enable_web_search"),
        key="enable_web_search",
        help=t(lang_code, "enable_web_search_help"),
        disabled=not search_available,
    )
    if not search_available:
        st.caption(t(lang_code, "tavily_missing_caption"))
        if st.session_state.enable_web_search:
            st.session_state.enable_web_search = False

    if st.button(t(lang_code, "start_new_session"), type="primary"):
        custom_option = t(lang_code, "subject_custom_option")
        current_subject = (
            st.session_state.subject_custom
            if st.session_state.subject_choice == custom_option
            else st.session_state.subject_choice
        )
        # Prevent duplicate sessions with same subject and goal
        existing = store.find_session_by_subject_goal(current_subject, st.session_state.goal or None)
        if existing:
            st.info(t(lang_code, "duplicate_session_loaded"))
            st.session_state.session_id = existing
            st.session_state.prev_session_id = existing
        else:
            lang_code = get_lang_code(st.session_state.language)
            session = lang_graph.start_session(
                subject=current_subject,
                goal=st.session_state.goal or None,
                language=lang_code,
            )
            # Reset quiz state when starting a new session
            _reset_quiz_ui_state()
            st.session_state.session_id = session.session_id
            st.session_state.prev_session_id = session.session_id

    st.markdown("---")
    st.subheader(t(lang_code, "history"))
    sessions = store.list_sessions()
    if sessions:
        labels = [
            f"{it.get('subject','')}: {it.get('goal','') or '-'}" for it in sessions
        ]
        choice = st.selectbox(t(lang_code, "load_session"), options=["-"] + labels, index=0)
        if choice != "-":
            idx = labels.index(choice)
            selected_id = sessions[idx]["session_id"]
            # Load selected session
            if selected_id != st.session_state.session_id:
                _reset_quiz_ui_state()
            st.session_state.session_id = selected_id
            st.session_state.prev_session_id = selected_id

            # Delete button below the selector
            if st.button(t(lang_code, "delete_this_session"), type="secondary"):
                if store.delete_session(selected_id):
                    st.success(t(lang_code, "session_deleted"))
                    st.rerun()
                else:
                    st.error(t(lang_code, "failed_delete_session"))
    else:
        st.caption(t(lang_code, "no_saved_sessions"))

# Title placed after sidebar to respect latest language selection in the same rerun
st.title(t(get_lang_code(st.session_state.get("language", "English")), "app_title"))


if not is_llm_configured():
    st.warning(t(lang_code, "llm_not_configured"), icon="⚠️")


def render_chat(session_id: str) -> None:
    session = store.load_session(session_id)
    # Apply pending actions before rendering any widgets
    if st.session_state.get("_to_send"):
        pending_text = st.session_state.pop("_to_send", "").strip()
        if pending_text:
            with st.spinner("Thinking..."):
                try:
                    _ = lang_graph.continue_session(
                        session_id=session_id,
                        user_message=pending_text,
                        enable_web_search=st.session_state.enable_web_search,
                    )
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.session_state["_clear_compose"] = True
            session = store.load_session(session_id)

    if st.session_state.get("_append_transcript"):
        transcript = st.session_state.pop("_append_transcript", "")
        current = st.session_state.get("compose_text", "")
        st.session_state["compose_text"] = (current + " " + transcript).strip()

    if st.session_state.get("_clear_compose"):
        st.session_state.pop("_clear_compose", None)
        st.session_state["compose_text"] = ""
    for msg in session.messages:
        if msg.role == "system":
            continue
        with st.chat_message(msg.role):
            st.markdown(msg.content)

    # Compose bar: text + mic/cancel/confirm + send
    try:
        from audio_recorder_streamlit import audio_recorder  # type: ignore
    except Exception:
        audio_recorder = None  # type: ignore

    if "compose_text" not in st.session_state:
        st.session_state.compose_text = ""
    if "recording_active" not in st.session_state:
        st.session_state.recording_active = False
    if "recorded_audio" not in st.session_state:
        st.session_state.recorded_audio = None

    # Layout: plus | text | mic | send
    compose_cols = st.columns([0.8, 8, 0.9, 0.9])
    with compose_cols[0]:
        st.button("＋", key="btn_plus")
    with compose_cols[1]:
        st.text_input("Ask anything", key="compose_text", label_visibility="collapsed")

    # Mic / Cancel control (3rd column)
    with compose_cols[2]:
        if not st.session_state.recording_active:
            if st.button("🎤", key="btn_mic"):
                st.session_state.recording_active = True
        else:
            if st.button("✖", key="btn_cancel_record"):
                st.session_state.recording_active = False
                st.session_state.recorded_audio = None

    # Send or Confirm control (4th column)
    with compose_cols[3]:
        if st.session_state.recording_active:
            if st.button("✔", key="btn_ok_record"):
                audio_bytes = st.session_state.recorded_audio
                if audio_bytes:
                    try:
                        raw_wav = ensure_wav_mono_16k(audio_bytes)
                        transcript = transcribe_wav_to_text(raw_wav)
                        if transcript:
                            st.session_state["_append_transcript"] = transcript
                    except Exception as exc:
                        st.error(str(exc))
                st.session_state.recording_active = False
                st.session_state.recorded_audio = None
                st.rerun()
        else:
            if st.button("➡️", key="btn_send", type="primary"):
                st.session_state["_to_send"] = st.session_state.get("compose_text", "")
                st.rerun()

    # Recorder widget rendered only when actively recording
    if st.session_state.recording_active and audio_recorder is not None:
        rec_audio = audio_recorder(text="", icon_size="2x")
        if rec_audio:
            st.session_state.recorded_audio = rec_audio

    # Styling for rounded compose bar and circular buttons
    input_dir_css = "direction: rtl; text-align: right;" if lang_code == "fa" else "direction: ltr; text-align: left;"
    st.markdown(
        f"""
        <style>
        section.main div[data-testid="stHorizontalBlock"]:last-of-type {{
            padding-top: 6px; padding-bottom: 6px; background-color: #1e1e1e;
            border-radius: 25px; margin: 10px 0; padding: 8px 12px;
        }}
        section.main div[data-testid="stHorizontalBlock"]:last-of-type div[data-testid="column"] {{
            padding-left: 4px; padding-right: 4px;
        }}
        /* Text input pill */
        section.main div[data-testid="stHorizontalBlock"]:last-of-type div[data-testid="column"]:nth-of-type(2) input {{
            background-color: #2f2f2f !important; border: 1px solid #3a3a3a !important;
            color: #ffffff !important; border-radius: 20px !important; height: 48px !important;
            padding: 12px 16px !important; {input_dir_css} font-size: 16px !important;
        }}
        /* Left plus button */
        section.main div[data-testid="stHorizontalBlock"]:last-of-type div[data-testid="column"]:nth-of-type(1) button {{
            background-color: #3a3a3a !important; color: #ffffff !important; border: 0 !important;
            border-radius: 50% !important; width: 44px; height: 44px; margin-top: 2px; font-size: 18px !important;
        }}
        /* Mic button */
        section.main div[data-testid="stHorizontalBlock"]:last-of-type div[data-testid="column"]:nth-of-type(3) button {{
            background-color: #3a3a3a !important; color: #ffffff !important; border: 0 !important;
            border-radius: 50% !important; width: 44px; height: 44px; margin-top: 2px; font-size: 18px !important;
        }}
        /* Send/Cancel/Confirm buttons */
        section.main div[data-testid="stHorizontalBlock"]:last-of-type div[data-testid="column"]:nth-of-type(4) button {{
            background-color: #3a3a3a !important; color: #ffffff !important; border: 0 !important;
            border-radius: 50% !important; width: 44px; height: 44px; margin-top: 2px; font-size: 14px !important;
        }}
        /* Primary send highlight */
        section.main div[data-testid="stHorizontalBlock"]:last-of-type div[data-testid="column"]:nth-of-type(4) button[kind="primary"] {{
            background: #ffffff !important; color: #000000 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


if st.session_state.session_id:
    render_chat(st.session_state.session_id)
    st.markdown("---")
    with st.expander(t(lang_code, "generate_mcq_quiz")):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            current_subject = (
                st.session_state.subject_custom
                if st.session_state.subject_choice == t(lang_code, "subject_custom_option")
                else st.session_state.subject_choice
            )
            topic = current_subject
            st.text_input(t(lang_code, "topic"), value=topic, key="quiz_topic")
        with col2:
            num = st.number_input(t(lang_code, "questions"), min_value=3, max_value=10, value=5, step=1, key="quiz_num")
        with col3:
            display_levels, level_map = difficulty_display_and_map(lang_code)
            display_choice = st.selectbox(t(lang_code, "difficulty"), display_levels, index=1, key="quiz_difficulty_display")
            st.session_state.quiz_difficulty = level_map[display_choice]

        # Create a new quiz
        if st.button(t(lang_code, "create_quiz"), type="primary"):
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
                        st.warning(t(lang_code, "topic_ignored", reason=reason))

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
                choice = st.radio(t(lang_code, "select_answer_for", idx=idx), options, index=None, key=widget_key, horizontal=False)
                if choice is not None:
                    sel_index = options.index(choice)
                    if sel_index == q.get("correct_index", -1):
                        st.success(t(lang_code, "correct") + q.get("explanation", ""))
                    else:
                        st.error(t(lang_code, "incorrect_prefix") + f"{options[q.get('correct_index', 0)]}\n\n{q.get('explanation','')}")
            # Scoring (computed on demand)
            if st.button(t(lang_code, "submit_answers"), type="secondary"):
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
                st.info(t(lang_code, "score_label", correct=correct, total=total))
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

            if st.button(t(lang_code, "generate_custom_lesson"), type="primary"):
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
                            language=getattr(session, "language", "en"),
                        )
                        st.markdown("### " + t(lang_code, "personalized_lesson"))
                        st.markdown(lesson)
                except Exception as exc:
                    st.error(str(exc))

    st.markdown("---")
    with st.expander(t(lang_code, "past_quiz_results")):
        results = quiz_store.list_results(session_id=st.session_state.session_id)
        if not results:
            st.caption("No quiz results yet.")
        else:
            for r in results:
                st.write(f"Session {r['session_id'][:8]}, Quiz {r['quiz_id'][:8]} • {r['topic']} — {r['correct_answers']}/{r['total_questions']}")
else:
    st.info(t(get_lang_code(st.session_state.get("language", "English")), "start_info"))


