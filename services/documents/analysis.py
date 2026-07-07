"""M2 — Analysis pipeline: summary + red flags + provenance.

Agentic RAG approach:
1. Retrieve relevant chunks from document_chunk (vector + keyword)
2. Generate summary_md (plain Polish)
3. Detect red_flags (onerous clauses, penalties, short deadlines)
4. Each red_flag MUST have provenance — unsupported claims are dropped.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from services.ai.clients import LLMClient
from services.documents.ocr import ExtractedDocument

logger = logging.getLogger(__name__)


@dataclass
class RedFlag:
    """A red-flag finding with provenance."""
    severity: str          # "critical", "high", "medium", "low"
    category: str          # e.g. "kary_umowne", "brak_waloryzacji"
    message: str           # Polish description
    provenance: dict       # {doc_id, page, line}
    confidence: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "provenance": self.provenance,
            "confidence": self.confidence,
        }


@dataclass
class Analysis:
    """Complete tender analysis result."""
    summary_md: str
    red_flags: list[RedFlag] = field(default_factory=list)
    key_facts: dict[str, Any] = field(default_factory=dict)
    przedmiar_items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_md": self.summary_md,
            "red_flags": [rf.to_dict() for rf in self.red_flags],
            "key_facts": self.key_facts,
            "przedmiar_items": self.przedmiar_items,
        }


# ──────────────────────────────────────────────────────────────────────────── #
# Red-flag detection rules (deterministic + LLM-enhanced)
# ──────────────────────────────────────────────────────────────────────────── #

import re

_REDFLAG_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    # (pattern, category, severity, message_template)
    (
        re.compile(r"kar[ayę]\s+umown[ąaey]\s*.*?(\d[,.]\d+)\s*%\s*/?\s*dzi", re.I),
        "kary_umowne",
        "high",
        "Kara umowna {0}%/dzień — powyżej bezpiecznego progu 0.3%/dzień",
    ),
    (
        re.compile(r"[Bb]rak\s+(klauzuli\s+)?waloryzac", re.I),
        "brak_waloryzacji",
        "critical",
        "Brak klauzuli waloryzacyjnej — przy umowie >6 mies. narusza art. 439 PZP",
    ),
    (
        re.compile(r"waloryzac[yj].*?brak|nie\s+przewiduje\s+si[eę]\s+waloryzac", re.I),
        "brak_waloryzacji",
        "critical",
        "Brak klauzuli waloryzacyjnej — ryzyko wzrostu kosztów bez możliwości korekty",
    ),
    (
        re.compile(r"wynagrodzeni[ae]\s+ryczałtow[ea]\s+nie\s*zmien", re.I),
        "brak_waloryzacji",
        "high",
        "Wynagrodzenie ryczałtowe niezmienne — brak waloryzacji",
    ),
    (
        re.compile(r"zabezpieczeni[ae]\s+.*?(\d{2,})\s*%", re.I),
        "znwu_wysokie",
        "high",
        "ZNWU {0}% — sprawdź czy nie przekracza limitu 10% (art. 449 PZP)",
    ),
    (
        re.compile(r"termin\s+(wykonania|realizacji)\s*:?\s*(\d{1,3})\s*dn", re.I),
        "krotki_termin",
        "medium",
        "Termin realizacji: {1} dni — oceń wykonalność przy zakresie robót",
    ),
    (
        re.compile(r"(\d[,.]\d+)\s*%\s*wynagrodzenia\s*(brutto)?\s*za\s*(każdy\s+)?dzi", re.I),
        "kary_umowne",
        "high",
        "Kara {0}% wynagrodzenia za dzień opóźnienia",
    ),
    (
        re.compile(r"odstąpieni[ae].*?(\d{1,2})\s*%\s*wynagrodzeni", re.I),
        "kara_odstapienie",
        "medium",
        "Kara za odstąpienie: {0}% wynagrodzenia",
    ),
]


def _detect_redflags_regex(text: str, *, doc_id: str = "") -> list[RedFlag]:
    """Deterministic red-flag detection using regex patterns."""
    flags: list[RedFlag] = []
    lines = text.split("\n")

    for line_idx, line in enumerate(lines):
        for pattern, category, severity, msg_template in _REDFLAG_PATTERNS:
            match = pattern.search(line)
            if match:
                # Format message with captured groups
                groups = match.groups()
                try:
                    message = msg_template.format(*groups)
                except (IndexError, KeyError):
                    message = msg_template

                # Find page (approximate from line position)
                page = 1 + line_idx // 50  # rough: 50 lines per page

                flags.append(RedFlag(
                    severity=severity,
                    category=category,
                    message=message,
                    provenance={
                        "doc_id": doc_id,
                        "page": page,
                        "line": line.strip()[:100],
                    },
                    confidence=0.85,
                ))
                break  # one flag per line

    return flags


def analyze_tender(
    doc_text: str,
    *,
    doc_id: str = "doc-001",
    llm: LLMClient,
    przedmiar_items: list[dict[str, Any]] | None = None,
) -> Analysis:
    """Full analysis pipeline: summary + red flags.

    Steps:
    1. Deterministic red-flag scan (regex)
    2. LLM-enhanced red-flag detection (if available)
    3. LLM summary generation
    4. Merge and validate (drop flags without provenance)
    """
    # Step 1: Deterministic red flags
    regex_flags = _detect_redflags_regex(doc_text, doc_id=doc_id)

    # Step 2: LLM red-flag detection
    llm_flags = _llm_detect_redflags(doc_text, llm, doc_id=doc_id)

    # Step 3: LLM summary
    summary_md = _generate_summary(doc_text, llm)

    # Merge flags (dedupe by category)
    all_flags = _merge_flags(regex_flags, llm_flags)

    # Validate: drop flags without provenance
    valid_flags = [f for f in all_flags if f.provenance and f.provenance.get("page")]

    return Analysis(
        summary_md=summary_md,
        red_flags=valid_flags,
        key_facts={},
        przedmiar_items=przedmiar_items or [],
    )


def _llm_detect_redflags(text: str, llm: LLMClient, *, doc_id: str) -> list[RedFlag]:
    """LLM-enhanced red-flag detection."""
    prompt = (
        "Przeanalizuj dokument przetargowy pod kątem ryzyk dla wykonawcy robót budowlanych.\n"
        "Szukaj: uciążliwe klauzule, wysokie kary, brak waloryzacji, krótkie terminy, "
        "asymetryczne zapisy, brak odwodnienia, niezgodności.\n"
        f"Tekst:\n{text[:3000]}\n"
        "Zwróć JSON: {\"red_flags\": [{\"severity\":\"high/medium/critical\", "
        "\"category\":\"...\", \"message\":\"...\", \"provenance\":{\"doc_id\":\"...\", "
        "\"page\":N, \"line\":\"...\"}, \"confidence\":0.0-1.0}]}"
    )
    try:
        resp = llm.generate(prompt, system="Wykrywanie ryzyk w dokumentach przetargowych.", json_mode=True)
        data = json.loads(resp)
        flags_raw = data.get("red_flags", [])
        return [
            RedFlag(
                severity=f.get("severity", "medium"),
                category=f.get("category", "other"),
                message=f.get("message", ""),
                provenance=f.get("provenance", {"doc_id": doc_id}),
                confidence=float(f.get("confidence", 0.7)),
            )
            for f in flags_raw
            if f.get("message") and f.get("provenance")
        ]
    except Exception as exc:
        logger.warning("LLM red-flag detection failed: %s", exc)
        return []


def _generate_summary(text: str, llm: LLMClient) -> str:
    """Generate Polish summary of tender document."""
    prompt = (
        "Napisz krótkie podsumowanie tego przetargu w języku polskim (3-5 zdań).\n"
        "Uwzględnij: przedmiot zamówienia, wartość, termin, najważniejsze wymagania.\n"
        f"Tekst:\n{text[:2000]}\n"
        "Zwróć JSON: {\"summary_md\": \"...\"}"
    )
    try:
        resp = llm.generate(prompt, system="Podsumowanie przetargu.", json_mode=True)
        data = json.loads(resp)
        return data.get("summary_md", "Brak podsumowania.")
    except Exception as exc:
        logger.warning("LLM summary failed: %s", exc)
        return "Podsumowanie niedostępne (błąd LLM)."


def _merge_flags(regex_flags: list[RedFlag], llm_flags: list[RedFlag]) -> list[RedFlag]:
    """Merge regex and LLM flags, deduplicating by category."""
    seen_categories: set[str] = set()
    merged: list[RedFlag] = []

    # Regex flags first (higher confidence)
    for f in regex_flags:
        if f.category not in seen_categories:
            seen_categories.add(f.category)
            merged.append(f)

    # Then LLM flags (new categories only)
    for f in llm_flags:
        if f.category not in seen_categories:
            seen_categories.add(f.category)
            merged.append(f)

    return merged
