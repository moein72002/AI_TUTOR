from __future__ import annotations

from typing import Dict, List, Tuple


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "app_title": "🎓 AI Tutor",
        "session": "Session",
        "subject": "Subject",
        "subject_custom_option": "Write your subject choice",
        "subject_custom_placeholder": "e.g., Linear Algebra",
        "learning_goal_optional": "Learning goal (optional)",
        "language": "Language",
        "enable_web_search": "Enable web search",
        "enable_web_search_help": "Augment answers with brief web findings when available.",
        "tavily_missing_caption": "Set TAVILY_API_KEY in .env to enable web search.",
        "start_new_session": "Start new session",
        "history": "History",
        "load_session": "Load session",
        "delete_this_session": "Delete this session",
        "no_saved_sessions": "No saved sessions yet.",
        "start_info": "Start a new session from the sidebar to begin.",
        "llm_not_configured": "LLM is not configured. Set OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL in your .env and restart the app.",
        "chat_input_placeholder": "Ask a question or describe a problem...",
        "generate_mcq_quiz": "Generate MCQ quiz",
        "topic": "Topic",
        "questions": "Questions",
        "difficulty": "Difficulty",
        "create_quiz": "Create quiz",
        "submit_answers": "Submit answers",
        "generate_custom_lesson": "Generate custom lesson",
        "past_quiz_results": "Past quiz results",
        "score_label": "Score: {correct} / {total}",
        "personalized_lesson": "Personalized lesson",
        "session_deleted": "Session deleted.",
        "failed_delete_session": "Failed to delete session.",
        "duplicate_session_loaded": "A session with the same subject and goal already exists. Loading it instead.",
        "topic_ignored": "The quiz topic was ignored: {reason}",
        "correct": "Correct! ",
        "incorrect_prefix": "Incorrect. Correct answer: ",
        "select_answer_for": "Select answer for Q{idx}",
    },
    "fa": {
        "app_title": "🎓 آموزگار هوشمند",
        "session": "جلسه",
        "subject": "موضوع",
        "subject_custom_option": "نوشتن موضوع دلخواه",
        "subject_custom_placeholder": "مثلاً: جبر خطی",
        "learning_goal_optional": "هدف یادگیری (اختیاری)",
        "language": "زبان",
        "enable_web_search": "جستجوی وب را فعال کن",
        "enable_web_search_help": "در صورت امکان پاسخ‌ها را با یافته‌های وب تقویت کن.",
        "tavily_missing_caption": "برای فعال‌سازی جستجو، TAVILY_API_KEY را در .env تنظیم کنید.",
        "start_new_session": "شروع جلسه جدید",
        "history": "تاریخچه",
        "load_session": "باز کردن جلسه",
        "delete_this_session": "حذف این جلسه",
        "no_saved_sessions": "هنوز جلسه‌ای ذخیره نشده است.",
        "start_info": "برای شروع، از نوار کناری یک جلسه جدید را آغاز کنید.",
        "llm_not_configured": "سامانه LLM پیکربندی نشده است. مقادیر OPENAI_API_KEY، OPENAI_BASE_URL و OPENAI_MODEL را در .env تنظیم کرده و برنامه را مجدداً اجرا کنید.",
        "chat_input_placeholder": "سوالی بپرسید یا مسئله‌ای را توضیح دهید...",
        "generate_mcq_quiz": "ساخت آزمون چندگزینه‌ای",
        "topic": "موضوع آزمون",
        "questions": "تعداد سوال‌ها",
        "difficulty": "سطح دشواری",
        "create_quiz": "ساخت آزمون",
        "submit_answers": "ثبت پاسخ‌ها",
        "generate_custom_lesson": "تولید درس شخصی‌سازی‌شده",
        "past_quiz_results": "نتایج آزمون‌های گذشته",
        "score_label": "امتیاز: {correct} / {total}",
        "personalized_lesson": "درس شخصی‌سازی‌شده",
        "session_deleted": "جلسه حذف شد.",
        "failed_delete_session": "حذف جلسه ناموفق بود.",
        "duplicate_session_loaded": "جلسه‌ای با همین موضوع و هدف موجود است؛ همان بارگذاری شد.",
        "topic_ignored": "موضوع آزمون نادیده گرفته شد: {reason}",
        "correct": "درست! ",
        "incorrect_prefix": "نادرست. پاسخ صحیح: ",
        "select_answer_for": "انتخاب پاسخ برای سوال {idx}",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in TRANSLATIONS else "en"
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def get_lang_code(selection: str) -> str:
    return "fa" if selection.strip() in ("فارسی", "fa", "Persian") else "en"


def popular_subjects_for_lang(lang: str) -> List[str]:
    if lang == "fa":
        return ["ریاضیات", "فیزیک", "شیمی", "زیست‌شناسی", "تاریخ", "برنامه‌نویسی"]
    return ["Mathematics", "Physics", "Chemistry", "Biology", "History", "Programming"]


def difficulty_display_and_map(lang: str) -> Tuple[List[str], Dict[str, str]]:
    if lang == "fa":
        display = ["آسان", "متوسط", "سخت"]
        mapping = {"آسان": "easy", "متوسط": "medium", "سخت": "hard"}
    else:
        display = ["easy", "medium", "hard"]
        mapping = {"easy": "easy", "medium": "medium", "hard": "hard"}
    return display, mapping


