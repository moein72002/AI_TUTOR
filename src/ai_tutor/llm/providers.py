from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

try:
    # OpenAI v1 SDK
    from openai import OpenAI  # type: ignore
except Exception as exc:  # pragma: no cover - import guard for environments without openai
    OpenAI = None  # type: ignore


class LlmConfiguration(BaseModel):
    api_key: str
    base_url: str
    model: str


def is_llm_configured(env: Optional[Dict[str, str]] = None) -> bool:
    environment = env if env is not None else os.environ
    return (
        bool(environment.get("OPENAI_API_KEY"))
        and bool(environment.get("OPENAI_BASE_URL"))
        and bool(environment.get("OPENAI_MODEL"))
    )


def read_llm_configuration(env: Optional[Dict[str, str]] = None) -> LlmConfiguration:
    environment = env if env is not None else os.environ
    api_key = environment.get("OPENAI_API_KEY", "").strip()
    base_url = environment.get("OPENAI_BASE_URL", "").strip()
    model = environment.get("OPENAI_MODEL", "").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError(
            "LLM is not configured. Ensure OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL are set."
        )
    return LlmConfiguration(api_key=api_key, base_url=base_url, model=model)


class OpenAIProvider:
    """Thin wrapper around OpenAI chat completions for our app.

    This abstraction avoids calling the LLM directly from the UI, as required by project rules.
    """

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        # Build a payload compatible with multiple backends. Some models (e.g., gpt-5-nano)
        # do not support temperature or max_tokens; proactively omit for gpt-5*.
        payload: Dict[str, object] = {
            "model": self._model,
            "messages": messages,
        }
        is_gpt5: bool = self._model.lower().startswith("gpt-5")
        if not is_gpt5 and max_tokens is not None:
            payload["max_tokens"] = max_tokens
        # Only set temperature if model supports it and caller changed from default 1
        if not is_gpt5 and temperature is not None and temperature != 1:
            payload["temperature"] = temperature

        def try_request(p: Dict[str, object]) -> str:
            response = self._client.chat.completions.create(**p)  # type: ignore[arg-type]
            choice = response.choices[0]
            return choice.message.content or ""

        # First attempt
        try:
            return try_request(payload)
        except Exception as exc:  # Fallbacks for parameter incompatibilities
            text = str(exc)
            # Handle unsupported max_tokens → retry with max_completion_tokens
            if "max_tokens" in payload and (
                "Unsupported parameter: 'max_tokens'" in text
                or "'max_tokens' is not supported" in text
            ):
                value = payload.pop("max_tokens")
                payload["max_completion_tokens"] = value  # type: ignore[assignment]
                try:
                    return try_request(payload)
                except Exception as exc2:
                    text = str(exc2)
                    # Continue to next fallback below

            # Handle unsupported temperature value → retry without temperature
            if "temperature" in payload and (
                "Unsupported value: 'temperature'" in text
                or "does not support" in text and "temperature" in text
            ):
                payload.pop("temperature", None)
                return try_request(payload)

            # If unknown failure, propagate original error
            raise


def get_llm_provider(env: Optional[Dict[str, str]] = None) -> OpenAIProvider:
    cfg = read_llm_configuration(env)
    if OpenAI is None:
        raise RuntimeError(
            "openai package is not available. Ensure dependencies are installed inside the container."
        )
    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
    return OpenAIProvider(client=client, model=cfg.model)


