"""vLLM Client — generate / generate_stream / embed.

Uses vLLM OpenAI-compatible API at VLLM_BASE_URL.
"""
from __future__ import annotations

import os
import httpx
from typing import Generator

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "axon")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "token-abc123")

TERRA_SYSTEM_PROMPT = """Jesteś budos — AI asystentem platformy YU-NA do zarządzania przetargami budowlanymi.
Odpowiadasz po polsku, zwięźle i merytorycznie. Pomagasz w:
- Analizie przetargów i SWZ
- Ocenie szans wygranej
- Strategii cenowej i kosztorysach
- Monitoringu rynku i konkurencji
Używaj danych z systemu do konkretnych odpowiedzi."""


class VLLMClient:
    def __init__(self):
        self.base_url = VLLM_BASE_URL
        self.model = VLLM_MODEL
        self.api_key = VLLM_API_KEY

    def generate(self, prompt: str, system: str = TERRA_SYSTEM_PROMPT, max_tokens: int = 1024) -> str:
        """Generate a single response."""
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def generate_stream(self, prompt: str, system: str = TERRA_SYSTEM_PROMPT, max_tokens: int = 1024) -> Generator[str, None, None]:
        """Stream tokens via SSE."""
        import json as _json

        with httpx.Client(timeout=120.0) as client:
            with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stream": True,
                },
            ) as resp:
                for line in resp.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (KeyError, _json.JSONDecodeError):
                        continue


_client: VLLMClient | None = None


def get_llm_client() -> VLLMClient:
    global _client
    if _client is None:
        _client = VLLMClient()
    return _client
