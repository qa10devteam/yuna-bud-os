"""Document classification — SWZ / design / STWiOR / przedmiar / other."""
from __future__ import annotations

import re
import logging
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from services.ai.clients import LLMClient

logger = logging.getLogger(__name__)


class DocKind(str, Enum):
    SWZ = "swz"
    DESIGN = "design"
    STWIOR = "stwior"
    PRZEDMIAR = "przedmiar"
    KOSZTORYS = "kosztorys"
    UMOWA = "umowa"
    OTHER = "other"


class ClassifyResult(NamedTuple):
    kind: DocKind
    confidence: float


# Heuristic patterns (filename + first page content)
_PATTERNS: list[tuple[re.Pattern, DocKind]] = [
    (re.compile(r"przedmiar", re.I), DocKind.PRZEDMIAR),
    (re.compile(r"kosztorys", re.I), DocKind.KOSZTORYS),
    (re.compile(r"swz|specyfikacja\s+warunk", re.I), DocKind.SWZ),
    (re.compile(r"stw[io]+r|specyfikacja\s+techniczna", re.I), DocKind.STWIOR),
    (re.compile(r"projekt\s+(budowlany|wykonawczy|techniczny)", re.I), DocKind.DESIGN),
    (re.compile(r"umow[ay]|wzór\s+umowy|istotne\s+postanowienia", re.I), DocKind.UMOWA),
]


def classify_document(
    filename: str,
    first_page_text: str = "",
    *,
    llm: LLMClient | None = None,
) -> ClassifyResult:
    """Classify document by filename + content heuristics + optional LLM.

    Priority: filename heuristics > content heuristics > LLM fallback.
    """
    # 1. Filename heuristics
    for pattern, kind in _PATTERNS:
        if pattern.search(filename):
            return ClassifyResult(kind=kind, confidence=0.90)

    # 2. Content heuristics (first page)
    if first_page_text:
        for pattern, kind in _PATTERNS:
            if pattern.search(first_page_text[:2000]):
                return ClassifyResult(kind=kind, confidence=0.80)

    # 3. LLM fallback
    if llm:
        import json
        prompt = (
            f"Zaklasyfikuj dokument budowlany.\n"
            f"Nazwa pliku: {filename}\n"
            f"Fragment treści: {first_page_text[:500]}\n"
            f"Zwróć JSON: {{\"kind\": \"swz|design|stwior|przedmiar|kosztorys|umowa|other\", \"confidence\": 0.0-1.0}}"
        )
        try:
            resp = llm.generate(prompt, system="Klasyfikuj dokument przetargowy.", json_mode=True)
            data = json.loads(resp)
            kind = DocKind(data.get("kind", "other"))
            conf = float(data.get("confidence", 0.5))
            return ClassifyResult(kind=kind, confidence=conf)
        except Exception as exc:
            logger.warning("LLM classify failed: %s", exc)

    return ClassifyResult(kind=DocKind.OTHER, confidence=0.3)
