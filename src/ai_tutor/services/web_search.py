from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx


class TavilySearchError(RuntimeError):
    pass


def is_tavily_configured(env: Optional[Dict[str, str]] = None) -> bool:
    environment = env if env is not None else os.environ
    return bool(environment.get("TAVILY_API_KEY"))


def tavily_search(query: str, max_results: int = 5, env: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    environment = env if env is not None else os.environ
    api_key = environment.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise TavilySearchError("TAVILY_API_KEY is not set.")

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": max_results,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
    except Exception as exc:  # pragma: no cover - network failures
        raise TavilySearchError(str(exc)) from exc

    results = data.get("results", [])
    simplified: List[Dict[str, str]] = []
    for item in results:
        simplified.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
            }
        )
    return simplified


