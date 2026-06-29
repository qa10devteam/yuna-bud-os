"""LLM Client protocol + StubClient for CI (zero-network)."""
from __future__ import annotations

import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM clients (OllamaClient, BedrockClient, StubClient)."""

    def generate(self, prompt: str, *, system: str = "", json_mode: bool = False) -> str:
        ...

    def embed(self, text: str) -> list[float]:
        ...


class StubClient:
    """Deterministic stub for CI — returns canned responses per task type.

    Used when TERRA_OFFLINE=1 or in tests. Ensures zero network calls.
    """

    def __init__(self) -> None:
        self._call_count = 0

    def generate(self, prompt: str, *, system: str = "", json_mode: bool = False) -> str:
        self._call_count += 1
        # Detect task from prompt content for appropriate stub response
        prompt_lower = prompt.lower()

        if "classify" in system.lower() or "dokument" in prompt_lower:
            return json.dumps({"kind": "przedmiar", "confidence": 0.85})

        if "red_flag" in system.lower() or "klauzul" in prompt_lower or "ryzyko" in prompt_lower:
            return json.dumps({
                "red_flags": [
                    {
                        "severity": "high",
                        "category": "kary_umowne",
                        "message": "Kara umowna 0.5%/dzień przekracza bezpieczny próg 0.3%/dzień",
                        "provenance": {"doc_id": "doc-001", "page": 12, "line": "§14 ust. 2"},
                        "confidence": 0.9,
                    }
                ]
            })

        if "summary" in system.lower() or "podsumow" in prompt_lower:
            return json.dumps({
                "summary_md": "## Podsumowanie przetargu\n\nPrzetarg na roboty ziemne i drogowe. "
                "Wartość szacunkowa: 850 000 PLN. Termin: 90 dni od podpisania umowy. "
                "Wymagane doświadczenie: min. 2 roboty o wartości >500 000 PLN w ostatnich 5 lat.",
                "key_facts": {
                    "value_pln": 850000,
                    "deadline_days": 90,
                    "experience_required": "2 roboty >500k PLN / 5 lat",
                },
            })

        if "przedmiar" in prompt_lower or "pozycj" in prompt_lower:
            return json.dumps({
                "items": [
                    {
                        "position_no": "1.1",
                        "description": "Wykopy mechaniczne w gruncie kat. III",
                        "unit": "m3",
                        "quantity": 1250.0,
                        "knr_code": "KNR 2-01 0211-03",
                        "page": 3,
                        "confidence": 0.92,
                    },
                    {
                        "position_no": "1.2",
                        "description": "Nasypy z gruntu kat. II z zagęszczeniem",
                        "unit": "m3",
                        "quantity": 800.0,
                        "knr_code": "KNR 2-01 0307-02",
                        "page": 3,
                        "confidence": 0.88,
                    },
                    {
                        "position_no": "1.3",
                        "description": "Transport urobku na odległość do 5 km",
                        "unit": "m3",
                        "quantity": 450.0,
                        "knr_code": "KNR 2-01 0510-01",
                        "page": 4,
                        "confidence": 0.90,
                    },
                ]
            })

        # Default generic response
        return json.dumps({"result": "ok", "confidence": 0.7})

    def embed(self, text: str) -> list[float]:
        """Return deterministic fake embedding (384-dim, content-based hash)."""
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        # Generate 384 dims from hash bytes (repeating)
        embedding = []
        for i in range(384):
            byte_val = h[i % 32]
            embedding.append((byte_val - 128) / 128.0)
        return embedding
