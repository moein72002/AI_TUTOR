import os

from ai_tutor.llm.providers import is_llm_configured, read_llm_configuration


def test_is_llm_configured_false(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert not is_llm_configured()


def test_is_llm_configured_true(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    assert is_llm_configured()


def test_read_llm_configuration_requires_env(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    try:
        read_llm_configuration()
    except RuntimeError as exc:
        assert "LLM is not configured" in str(exc)
    else:  # pragma: no cover - safety
        assert False, "Expected RuntimeError when env is missing"


