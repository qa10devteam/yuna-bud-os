"""VLLMClient — OpenAI-compatible client for self-hosted vLLM inference.

Connects to vLLM server (Qwen2.5-20B-Instruct-AWQ on EC2 g5.2xlarge).
Falls back to StubClient when TERRA_OFFLINE=1 or server unreachable.

Environment:
  VLLM_BASE_URL   — e.g. http://10.0.1.10:8000/v1  (default: http://localhost:8000/v1)
  VLLM_MODEL      — model name served by vLLM (default: Qwen/Qwen2.5-20B-Instruct-AWQ)
  VLLM_API_KEY    — optional API key (default: "token-terra")
  TERRA_OFFLINE   — if "1", skip network and use StubClient
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Generator

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8001/v1")
_DEFAULT_MODEL = os.environ.get("VLLM_MODEL", "axon")
_DEFAULT_API_KEY = os.environ.get("VLLM_API_KEY", "token-terra")

# System prompt that defines the model as Terra.OS operator
TERRA_SYSTEM_PROMPT = """\
Jesteś AXON — inteligentnym asystentem platformy Terra.OS do analizy przetargów budowlanych.

Twoje kompetencje:
- Analiza dokumentacji przetargowej (SWZ, przedmiary, umowy)
- Identyfikacja ryzyk i red flags w warunkach zamówienia
- Wsparcie kosztorysowania (KNR, stawki rynkowe, benchmarki Intercenbud)
- Ocena wykonalności (zasoby, terminy, warunki)
- Rekomendacje decyzyjne (GO / NO-GO / NEGOCJUJ) z uzasadnieniem
- Odpowiedzi o flow platformy i jak korzystać z modułów

Zasady:
1. Odpowiadasz ZAWSZE po polsku
2. Podajesz konkretne dane liczbowe gdy masz je w kontekście
3. Nigdy nie zgadujesz — gdy brak danych mówisz wprost
4. Jesteś precyzyjny i zwięzły — max 3-4 zdania na odpowiedź chyba że temat wymaga więcej
5. Formatujesz odpowiedzi w Markdown (bold kluczowe wartości, listy, nagłówki)
6. Przy analizie ryzyk zawsze podajesz severity: high/medium/low
7. Nie używasz emoji w odpowiedziach technicznych
"""


class VLLMClient:
    """Production LLM client connecting to self-hosted vLLM (OpenAI API compatible)."""

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        api_key: str = _DEFAULT_API_KEY,
        timeout: float = 30.0,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = httpx.Client(timeout=timeout)

    def generate(self, prompt: str, *, system: str = "", json_mode: bool = False) -> str:
        """Synchronous generation via /chat/completions."""
        messages = []
        sys_prompt = system or TERRA_SYSTEM_PROMPT
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"VLLMClient.generate failed: {e}")
            raise

    def generate_stream(self, prompt: str, *, system: str = "") -> Generator[str, None, None]:
        """Streaming generation via SSE — yields token chunks."""
        messages = []
        sys_prompt = system or TERRA_SYSTEM_PROMPT
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except Exception as e:
            logger.error(f"VLLMClient.generate_stream failed: {e}")
            raise

    def embed(self, text: str) -> list[float]:
        """Generate embeddings via /embeddings endpoint."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = self._client.post(
                f"{self.base_url}/embeddings",
                json={"model": self.model, "input": text},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"VLLMClient.embed failed: {e}")
            raise


def get_llm_client():
    """Factory: return VLLMClient (production) or StubClient (offline/CI).

    Logic:
    1. TERRA_OFFLINE=1 → StubClient (zero network)
    2. Otherwise → VLLMClient (may fail at call time if server down)
    """
    if os.environ.get("TERRA_OFFLINE", "0") == "1":
        from services.ai.clients import StubClient
        logger.info("TERRA_OFFLINE=1 — using StubClient")
        return StubClient()

    logger.info(f"Using VLLMClient → {_DEFAULT_BASE_URL} model={_DEFAULT_MODEL}")
    return VLLMClient()
