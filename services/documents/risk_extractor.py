"""S66/S67 — Risk Extractor: ekstrakcja flag ryzyka z dokumentów SWZ."""
from __future__ import annotations

import re


def extract_risk_flags(text: str) -> list[str]:
    """Ekstrahuj flagi ryzyka z tekstu dokumentu SWZ.

    Zwraca listę flag, np.:
      - 'kara_umowna_15pct' — kara umowna > 10%
      - 'high_financial_req' — wymagania finansowe (obrót > 100 000)
      - 'zabezpieczenie_15pct' — zabezpieczenie należytego wykonania > 10%
    """
    flags: list[str] = []

    # kary umowne > 10%
    for m in re.finditer(r"kar[ayę]\s+umown[aą].*?(\d+)\s*%", text, re.IGNORECASE):
        try:
            val = int(m.group(1))
            if val > 10:
                flags.append(f"kara_umowna_{val}pct")
        except (ValueError, IndexError):
            pass
    # fallback: "kar" + "%" w jednym zdaniu
    if not any(f.startswith("kara_umowna") for f in flags):
        for m in re.finditer(r"kar[ayę].*?(\d+)\s*%", text, re.IGNORECASE):
            try:
                val = int(m.group(1))
                if val > 10:
                    flags.append(f"kara_umowna_{val}pct")
                    break
            except (ValueError, IndexError):
                pass

    # wymagania finansowe — obrót + liczba 6+ cyfr
    if re.search(r"obrót.*?(\d{6,})", text, re.IGNORECASE):
        flags.append("high_financial_req")

    # zabezpieczenie należytego wykonania > 10%
    for m in re.finditer(r"zabezpieczeni[ae].*?(\d+)\s*%", text, re.IGNORECASE):
        try:
            val = int(m.group(1))
            if val > 10:
                flags.append(f"zabezpieczenie_{val}pct")
        except (ValueError, IndexError):
            pass

    # deduplicate preserving order
    seen: set[str] = set()
    deduped = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return deduped


def risk_level(flags: list[str]) -> tuple[str, float]:
    """Oblicz poziom ryzyka na podstawie flag.

    Returns:
        (level, score) — level: 'low'|'mid'|'high', score: 0.1|0.5|0.9
    """
    if len(flags) >= 3:
        return "high", 0.9
    if len(flags) >= 1:
        return "mid", 0.5
    return "low", 0.1
