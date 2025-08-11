from __future__ import annotations

import os
from typing import Dict, List

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def _is_gpt5(model: str) -> bool:
    return model.lower().startswith("gpt-5")


def get_langchain_chat() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError(
            "LLM is not configured. Ensure OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL are set."
        )
    # For gpt-5* omit temperature/max tokens to avoid unsupported params
    if _is_gpt5(model):
        return ChatOpenAI(model=model, api_key=api_key, base_url=base_url)
    # Default conservative temperature
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0)


def convert_dict_messages_to_langchain(messages: List[Dict[str, str]]):
    converted = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            converted.append(SystemMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=content))
    return converted


