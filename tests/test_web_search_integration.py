import pytest

from ai_tutor.services.web_search import tavily_search


def test_tavily_search_real_call():
    results = tavily_search("OpenAI latest news", max_results=1)
    assert isinstance(results, list)
    assert len(results) <= 1
    if results:
        assert "title" in results[0] and "url" in results[0]


