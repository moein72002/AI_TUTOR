from ai_tutor.graph.tutor import build_system_prompt


def test_system_prompt_includes_subject_and_goal() -> None:
    prompt = build_system_prompt(subject="Mathematics", goal="Learn derivatives")
    assert "Mathematics" in prompt
    assert "Learn derivatives" in prompt
    assert "Socratic" in prompt


