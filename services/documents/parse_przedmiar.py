"""Parse przedmiar (bill of quantities) from extracted text.

Extracts: position_no, description, unit, quantity, knr_code, page.
Supports both text-layer and VLM-OCR output.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from services.ai.clients import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class PrzedmiarItem:
    """Single position from a przedmiar (bill of quantities)."""
    position_no: str
    description: str
    unit: str
    quantity: float
    knr_code: str | None = None
    page: int | None = None
    confidence: float = 0.9

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_no": self.position_no,
            "description": self.description,
            "unit": self.unit,
            "quantity": self.quantity,
            "knr_code": self.knr_code,
            "page": self.page,
            "confidence": self.confidence,
        }


# Regex patterns for typical przedmiar line formats
# Format: "1.1 | Opis | m3 | 1250.00 | KNR 2-01 ..."
_LINE_PATTERN = re.compile(
    r"^\s*(?P<pos>\d+\.\d+)\s*[|\t]+\s*"
    r"(?P<desc>.+?)\s*[|\t]+\s*"
    r"(?P<unit>m[23]|mb|szt|t|km|kpl|kg|ha)\s*[|\t]+\s*"
    r"(?P<qty>[\d\s]+[.,]?\d*)\s*"
    r"(?:[|\t]+\s*(?P<knr>KNR[\w\s\-/]+))?"
    r"\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Alternative: KNR code in description
_KNR_IN_DESC = re.compile(r"(KNR\s*\d[\w\-/\s]*\d{4}[\-\s]\d{2})", re.I)

# Units
VALID_UNITS = {"m3", "m2", "mb", "m", "szt", "t", "km", "kpl", "kg", "ha", "mp"}


def parse_przedmiar(
    text: str,
    *,
    page_offset: int = 1,
    llm: LLMClient | None = None,
) -> list[PrzedmiarItem]:
    """Parse przedmiar text into structured items.

    Strategy:
    1. Try regex extraction (fast, high confidence)
    2. If regex yields <3 items and LLM available → LLM extraction
    """
    items = _regex_parse(text, page_offset=page_offset)

    if len(items) < 3 and llm:
        logger.info("Regex found only %d items, trying LLM extraction", len(items))
        llm_items = _llm_parse(text, llm, page_offset=page_offset)
        if len(llm_items) > len(items):
            items = llm_items

    logger.info("Parsed %d przedmiar items", len(items))
    return items


def _regex_parse(text: str, *, page_offset: int = 1) -> list[PrzedmiarItem]:
    """Fast regex-based extraction."""
    items: list[PrzedmiarItem] = []
    for match in _LINE_PATTERN.finditer(text):
        pos = match.group("pos")
        desc = match.group("desc").strip()
        unit = match.group("unit").lower()
        qty_str = match.group("qty").replace(" ", "").replace(",", ".")
        knr = match.group("knr")

        try:
            qty = float(qty_str)
        except ValueError:
            continue

        # Try to find KNR in description if not in dedicated column
        if not knr:
            knr_match = _KNR_IN_DESC.search(desc)
            if knr_match:
                knr = knr_match.group(1).strip()

        items.append(PrzedmiarItem(
            position_no=pos,
            description=desc,
            unit=unit,
            quantity=qty,
            knr_code=knr.strip() if knr else None,
            page=page_offset,
            confidence=0.90,
        ))

    return items


def _llm_parse(text: str, llm: LLMClient, *, page_offset: int = 1) -> list[PrzedmiarItem]:
    """LLM-based extraction for complex/non-standard formats."""
    prompt = (
        "Wyciągnij pozycje z przedmiaru robót budowlanych.\n"
        "Dla każdej pozycji podaj: position_no, description, unit (m3/m2/mb/szt/t/km), "
        "quantity (liczba), knr_code (jeśli podany), page.\n"
        f"Tekst:\n{text[:3000]}\n"
        "Zwróć JSON: {\"items\": [{\"position_no\": ..., \"description\": ..., ...}]}"
    )
    try:
        resp = llm.generate(prompt, system="Ekstrakcja przedmiaru robót.", json_mode=True)
        data = json.loads(resp)
        items_raw = data.get("items", [])
        return [
            PrzedmiarItem(
                position_no=str(it.get("position_no", "")),
                description=str(it.get("description", "")),
                unit=str(it.get("unit", "m3")).lower(),
                quantity=float(it.get("quantity", 0)),
                knr_code=it.get("knr_code"),
                page=it.get("page", page_offset),
                confidence=float(it.get("confidence", 0.75)),
            )
            for it in items_raw
            if it.get("description") and it.get("quantity")
        ]
    except Exception as exc:
        logger.warning("LLM parse failed: %s", exc)
        return []
