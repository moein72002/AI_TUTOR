from __future__ import annotations

import io
from typing import Optional

from ai_tutor.llm.providers import read_llm_configuration


def ensure_wav_mono_16k(raw_wav: bytes) -> bytes:
    # Pass-through; Whisper accepts various PCM WAV inputs.
    return raw_wav


def transcribe_wav_to_text(raw_wav: bytes, model: str = "whisper-1") -> str:
    """Transcribe a WAV byte stream using OpenAI Whisper via env config.

    Uses OPENAI_API_KEY and OPENAI_BASE_URL from .env (same as chat provider).
    """
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("openai package not installed in environment") from exc

    cfg = read_llm_configuration()
    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)

    buffer = io.BytesIO(raw_wav)
    # name is required by the SDK to infer filename/content-type
    buffer.name = "audio.wav"  # type: ignore[attr-defined]
    response = client.audio.transcriptions.create(model=model, file=buffer)
    return getattr(response, "text", "") or ""


