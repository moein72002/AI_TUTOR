from __future__ import annotations

import os
import sys
from typing import Optional

from dotenv import load_dotenv


def read_env() -> tuple[str, str, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()
    if not api_key or not base_url or not model:
        missing = [
            name
            for name, val in (
                ("OPENAI_API_KEY", api_key),
                ("OPENAI_BASE_URL", base_url),
                ("OPENAI_MODEL", model),
            )
            if not val
        ]
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. Configure them in .env and try again."
        )
    return api_key, base_url, model


def main() -> int:
    load_dotenv()  # load .env from project root if present

    try:
        api_key, base_url, model = read_env()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:
        print("ERROR: openai package is not installed. Run inside the Docker container or install dependencies.")
        print(str(exc))
        return 3

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello"}],
        )
        message = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        usage_text = (
            f" (tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens})"
            if usage
            else ""
        )
        print(f"OK: Model '{model}' responded: {message[:120].strip()}{usage_text}")
        return 0
    except Exception as exc:
        print(f"ERROR: LLM call failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


