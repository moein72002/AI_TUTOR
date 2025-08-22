from __future__ import annotations

from typing import Dict, List

from ai_tutor.llm.providers import get_llm_provider


def build_remediation_prompt(subject: str, topic: str, quiz: Dict, incorrect_indices: List[int], language: str = "en") -> List[Dict[str, str]]:
    system = (
        "You are a kind, effective tutor. Diagnose misconceptions and teach with concise steps, examples, and quick checks."
    )
    if language.lower().startswith("fa"):
        system += " Respond in Persian (Farsi)."
    mistakes_summary_lines: List[str] = []
    for i in incorrect_indices:
        try:
            q = quiz["questions"][i]
            mistakes_summary_lines.append(
                f"Q{i+1}: {q['question']} | Correct: {q['options'][q['correct_index']]}"
            )
        except Exception:
            continue
    mistakes_summary = "\n".join(mistakes_summary_lines) if mistakes_summary_lines else "(none)"
    user = (
        f"Subject: {subject}. Topic: {topic}.\n"
        "Create a brief personalized lesson to address the mistakes below.\n"
        "For each mistake: explain the core concept, show a clear example, and include a quick 1-question check.\n"
        f"Mistakes:\n{mistakes_summary}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generate_remediation(subject: str, topic: str, quiz: Dict, incorrect_indices: List[int], language: str = "en") -> str:
    provider = get_llm_provider()
    messages = build_remediation_prompt(subject=subject, topic=topic, quiz=quiz, incorrect_indices=incorrect_indices, language=language)
    return provider.generate(messages=messages, temperature=0)


