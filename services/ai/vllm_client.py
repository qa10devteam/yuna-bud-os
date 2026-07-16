"""LLM Client — multi-backend: Bedrock Claude (primary) → vLLM (fallback).

Hierarchy:
1. AWS Bedrock eu-west-1 claude-sonnet-4-6 (always available on EC2 role)
2. VLLM_BASE_URL (local vLLM if running on port 8001)
3. OpenAI-compatible endpoint via OPENAI_API_KEY
"""
from __future__ import annotations

import json
import logging
import os
from typing import Generator

logger = logging.getLogger(__name__)

# ─── env ─────────────────────────────────────────────────────────────────────

BEDROCK_REGION = os.getenv("BEDROCK_REGION", "eu-west-1")
BEDROCK_MODEL  = os.getenv("BEDROCK_MODEL", "eu.anthropic.claude-sonnet-4-6")

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
VLLM_MODEL    = os.getenv("VLLM_MODEL", "axon")
VLLM_API_KEY  = os.getenv("VLLM_API_KEY", "token-abc123")

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

TERRA_SYSTEM_PROMPT = """Jesteś budos — AI asystentem platformy YU-NA do zarządzania przetargami budowlanymi.
Odpowiadasz po polsku, zwięźle i merytorycznie. Pomagasz w:
- Analizie przetargów i SWZ
- Ocenie szans wygranej
- Strategii cenowej i kosztorysach
- Monitoringu rynku i konkurencji
Używaj danych z systemu do konkretnych odpowiedzi."""


# ─── Bedrock backend ─────────────────────────────────────────────────────────

def _bedrock_generate(prompt: str, system: str, max_tokens: int = 1024, *, json_mode: bool = False) -> str:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2 if json_mode else 0.7,
    }
    resp = client.invoke_model(
        modelId=BEDROCK_MODEL,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(resp["body"].read())
    return result["content"][0]["text"]


def _bedrock_stream(prompt: str, system: str, max_tokens: int = 1024) -> Generator[str, None, None]:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    resp = client.invoke_model_with_response_stream(
        modelId=BEDROCK_MODEL,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    for event in resp.get("body", []):
        chunk = event.get("chunk")
        if not chunk:
            continue
        data = json.loads(chunk["bytes"])
        if data.get("type") == "content_block_delta":
            delta = data.get("delta", {})
            text = delta.get("text", "")
            if text:
                yield text


# ─── vLLM backend ────────────────────────────────────────────────────────────

def _vllm_available() -> bool:
    import httpx
    try:
        r = httpx.get(f"{VLLM_BASE_URL}/models", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def _vllm_generate(prompt: str, system: str, max_tokens: int = 1024) -> str:
    import httpx
    resp = httpx.post(
        f"{VLLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {VLLM_API_KEY}"},
        json={
            "model": VLLM_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _vllm_stream(prompt: str, system: str, max_tokens: int = 1024) -> Generator[str, None, None]:
    import httpx
    with httpx.stream(
        "POST",
        f"{VLLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {VLLM_API_KEY}"},
        json={
            "model": VLLM_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": True,
        },
        timeout=60.0,
    ) as resp:
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                text = chunk["choices"][0].get("delta", {}).get("content")
                if text:
                    yield text
            except Exception:
                continue


# ─── Unified client ───────────────────────────────────────────────────────────

class VLLMClient:
    """Unified LLM client: Bedrock → vLLM → OpenAI."""

    def generate(
        self,
        prompt: str,
        system: str = TERRA_SYSTEM_PROMPT,
        max_tokens: int = 1024,
        *,
        json_mode: bool = False,
    ) -> str:
        # Try Bedrock first
        try:
            return _bedrock_generate(prompt, system, max_tokens, json_mode=json_mode)
        except Exception as e:
            logger.warning("Bedrock generate failed: %s — trying vLLM", e)

        # Try vLLM
        if _vllm_available():
            try:
                return _vllm_generate(prompt, system, max_tokens)
            except Exception as e2:
                logger.warning("vLLM generate failed: %s", e2)

        # OpenAI fallback
        if OPENAI_API_KEY:
            try:
                import httpx
                resp = httpx.post(
                    f"{OPENAI_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": OPENAI_MODEL,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                    },
                    timeout=60.0,
                )
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e3:
                logger.warning("OpenAI fallback failed: %s", e3)

        return "Przepraszam — brak dostępu do modelu AI w tym momencie."

    def generate_stream(
        self,
        prompt: str,
        system: str = TERRA_SYSTEM_PROMPT,
        max_tokens: int = 1024,
    ) -> Generator[str, None, None]:
        # Try Bedrock stream
        try:
            yield from _bedrock_stream(prompt, system, max_tokens)
            return
        except Exception as e:
            logger.warning("Bedrock stream failed: %s — trying vLLM", e)

        # Try vLLM stream
        if _vllm_available():
            try:
                yield from _vllm_stream(prompt, system, max_tokens)
                return
            except Exception as e2:
                logger.warning("vLLM stream failed: %s", e2)

        # Non-streaming fallback via generate
        try:
            text = self.generate(prompt, system, max_tokens)
            yield text
        except Exception as e3:
            yield f"Błąd AI: {e3}"


_client: VLLMClient | None = None


def get_llm_client() -> VLLMClient:
    global _client
    if _client is None:
        _client = VLLMClient()
    return _client
