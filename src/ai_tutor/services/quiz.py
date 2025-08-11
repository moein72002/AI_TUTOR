from __future__ import annotations

import json
import re
import uuid
import time
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from ai_tutor.llm.providers import get_llm_provider


Difficulty = Literal["easy", "medium", "hard"]


class MCQQuestion(BaseModel):
    question: str
    options: List[str] = Field(min_items=2)
    correct_index: int
    explanation: str


class QuizMeta(BaseModel):
    topic_used: bool = True
    ignored_reason: Optional[str] = None


class MCQQuiz(BaseModel):
    quiz_id: str
    subject: str
    topic: str
    difficulty: Difficulty
    questions: List[MCQQuestion] = Field(min_items=1)
    meta: Optional[QuizMeta] = None


def _build_quiz_prompt(subject: str, topic: str, difficulty: Difficulty, num_questions: int, context: str) -> List[dict]:
    system = (
        "You are an expert educator. Create a concise multiple-choice quiz. "
        "Return ONLY strict JSON (no markdown, no text before/after)."
    )
    user = (
        f"Subject: {subject}. Topic: {topic}. Difficulty: {difficulty}. Number of questions: {num_questions}.\n"
        "If the topic is clearly irrelevant to the subject and context, IGNORE the topic and generate the quiz for the subject instead.\n"
        "Include a 'meta' object indicating whether the topic was used and, if not, a brief reason.\n"
        f"Base questions on the following teaching context when relevant to the topic (may include prior Q&A):\n{context}\n"
        "Each question must have exactly 4 options. Use 0-based 'correct_index'. Provide a brief 'explanation' for the correct answer.\n"
        "JSON schema: {\n  'subject': str,\n  'topic': str,\n  'difficulty': 'easy'|'medium'|'hard',\n  'questions': [ { 'question': str, 'options': [str, str, str, str], 'correct_index': int, 'explanation': str } ],\n  'meta': { 'topic_used': bool, 'ignored_reason': str }\n}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _extract_json(text: str) -> str:
    # Attempt to extract the largest JSON object from the text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def generate_mcq_quiz(
    subject: str,
    topic: str,
    conversation_messages: List[dict],
    num_questions: int = 5,
    difficulty: Difficulty = "medium",
) -> MCQQuiz:
    provider = get_llm_provider()
    # Build prompt with exact chat context for better alignment
    # Concatenate last ~20 messages to keep context bounded
    ctx_msgs = conversation_messages[-20:]
    context = "\n\n".join([f"{m.get('role','user')}: {m.get('content','')}" for m in ctx_msgs])
    messages = _build_quiz_prompt(
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        num_questions=num_questions,
        context=context,
    )
    # Try with context; on transient errors, retry once then fallback to topic-only
    used_fallback = False
    try:
        raw = provider.generate(messages=messages, temperature=0)
    except Exception:
        time.sleep(0.6)
        try:
            raw = provider.generate(messages=messages, temperature=0)
        except Exception:
            fallback_messages = _build_quiz_prompt(
                subject=subject, topic=topic, difficulty=difficulty, num_questions=num_questions, context=""
            )
            raw = provider.generate(messages=fallback_messages, temperature=0)
            used_fallback = True
    # Parse JSON
    try:
        data = json.loads(raw)
    except Exception:
        try:
            data = json.loads(_extract_json(raw))
        except Exception as exc:
            raise RuntimeError(f"Failed to parse quiz JSON: {exc}\nRaw: {raw[:300]}")
    # Validate
    try:
        # Assign quiz_id if missing
        if "quiz_id" not in data:
            data["quiz_id"] = uuid.uuid4().hex
        # If meta missing, infer topic usage heuristically
        if "meta" not in data:
            # naive heuristic: if topic appears nowhere in questions/options, assume ignored
            text_blob = "\n".join(
                [q.get("question", "") + "\n" + "\n".join(q.get("options", [])) for q in data.get("questions", [])]
            ).lower()
            topic_used = topic.lower() in text_blob if topic else True
            data["meta"] = {
                "topic_used": bool(topic_used),
                "ignored_reason": (None if topic_used else "The requested topic was not reflected in the generated questions."),
            }
        quiz = MCQQuiz.model_validate(data)
    except ValidationError as exc:
        raise RuntimeError(f"Quiz validation failed: {exc}")

    # If we had to fallback and topic seems unused, enrich the reason
    if used_fallback and quiz.meta and not quiz.meta.topic_used and not quiz.meta.ignored_reason:
        quiz.meta.ignored_reason = "Transient generation error occurred; fell back to a safer prompt and the topic may have been ignored."
    return quiz


