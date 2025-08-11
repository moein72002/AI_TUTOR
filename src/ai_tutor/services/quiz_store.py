from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class QuizResult:
    session_id: str
    quiz_id: str
    topic: str
    total_questions: int
    correct_answers: int
    # Selected answers as indices aligned with quiz.questions
    selected_indices: list[int]
    # Indices of questions answered incorrectly
    incorrect_indices: list[int]


class QuizStore:
    def __init__(self, base_dir: Path | str = Path("data")) -> None:
        self.base_dir: Path = Path(base_dir)
        self.quizzes_dir: Path = self.base_dir / "quizzes"
        self.results_dir: Path = self.base_dir / "quiz_results"
        self.quizzes_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_quiz(self, session_id: str, quiz_id: str, payload: Dict) -> None:
        path = self.quizzes_dir / f"{session_id}__{quiz_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_quiz(self, session_id: str, quiz_id: str) -> Dict:
        path = self.quizzes_dir / f"{session_id}__{quiz_id}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw

    def save_result(self, result: QuizResult) -> None:
        path = self.results_dir / f"{result.session_id}__{result.quiz_id}.json"
        payload = {
            "session_id": result.session_id,
            "quiz_id": result.quiz_id,
            "topic": result.topic,
            "total_questions": result.total_questions,
            "correct_answers": result.correct_answers,
            "selected_indices": result.selected_indices,
            "incorrect_indices": result.incorrect_indices,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_results(self, session_id: Optional[str] = None) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        for file in sorted(self.results_dir.glob("*.json")):
            raw = json.loads(file.read_text(encoding="utf-8"))
            if session_id and raw.get("session_id") != session_id:
                continue
            items.append(raw)
        return items


