"""Local-mode highlight LLM — OpenAI, Gemini, or Ollama, per ``LLM_PROVIDER``."""
from __future__ import annotations

import requests
import os

from ...config import (
    GEMINI_MODEL,
    LLM_PROVIDER,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OPENAI_MODEL,
    require_gemini_key,
    require_openai_key,
)


def call_openai_llm(prompt: str) -> str:
    """OpenAI Chat Completions backend (``LLM_PROVIDER=openai``)."""
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "openai is required for LLM_PROVIDER=openai. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    client = OpenAI(api_key=require_openai_key())
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def call_gemini_llm(prompt: str) -> str:
    """Google Gemini backend (``LLM_PROVIDER=gemini``)."""
    try:
        from google import genai  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "google-genai is required for LLM_PROVIDER=gemini. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    client = genai.Client(api_key=require_gemini_key())
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
            "max_output_tokens": 8192,
        },
    )
    return response.text or ""


def call_ollama_llm(prompt: str) -> str:
    """Fully offline Ollama backend (``LLM_PROVIDER=ollama``)."""
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.2}},
        timeout=600,
    )
    response.raise_for_status()
    return response.json()["response"]


def call_local_llm(prompt: str) -> str:
    """Dispatch to the configured local LLM provider."""
    provider = (LLM_PROVIDER or "openai").strip().lower()
    if provider == "compatible":
        return call_compatible_llm(prompt)
    if provider == "openai":
        return call_openai_llm(prompt)
    if provider == "gemini":
        return call_gemini_llm(prompt)
    if provider == "ollama":
        return call_ollama_llm(prompt)
    raise RuntimeError(
        f"Unknown LLM_PROVIDER={provider!r}. Use 'openai', 'gemini', 'ollama', or 'compatible'."
    )


def call_compatible_llm(prompt: str) -> str:
    """LM Studio, llama.cpp, vLLM, or hosted Chat Completions servers."""
    base = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1").rstrip("/")
    key = os.getenv("LLM_API_KEY", "")
    response = requests.post(base + "/chat/completions",
        headers={"Authorization": "Bearer " + key} if key else {},
        json={"model": os.getenv("LLM_MODEL", "local-model"),
              "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
        timeout=600)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
