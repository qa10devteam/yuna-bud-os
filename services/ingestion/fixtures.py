"""M1 — Fixture-based connectors for BZP/TED/BK (used in tests and offline mode).

When TERRA_OFFLINE=1 or DB unreachable, ingestion falls back to fixtures.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bzp_connector import BZPRawNotice

FIXTURES_DIR = Path(__file__).parent.parent.parent / "tests" / "fixtures"


def load_bzp_fixtures() -> list[BZPRawNotice]:
    """Load BZP fixture notices from tests/fixtures/bzp_notices.json."""
    fp = FIXTURES_DIR / "bzp_notices.json"
    if not fp.exists():
        return _default_bzp_fixtures()
    with fp.open(encoding="utf-8") as f:
        data = json.load(f)
    return [BZPRawNotice(n) for n in data]


def _default_bzp_fixtures() -> list[BZPRawNotice]:
    """Built-in fixture notices for M1 acceptance tests."""
    return [
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00262955/01",
            "noticePublicationDate": "2024-03-15",
            "procurementObject": "Budowa drogi gminnej nr 101234D w miejscowości Pieszyce wraz z odwodnieniem",
            "cpvCodes": ["45233120-6", "45111200-0"],
            "estimatedValue": 850000.0,
            "submissionDeadlineDate": "2024-04-05T10:00:00",
            "orderingPartyName": "Gmina Pieszyce",
            "orderingPartyAddress": "ul. Kościuszki 2, 58-250 Pieszyce",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
            "procedureType": "TP",  # Tryb Podstawowy
            "sourceKind": "bzp",
        }),
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00298771/01",
            "noticePublicationDate": "2024-03-20",
            "procurementObject": "Przebudowa rowów melioracyjnych i roboty ziemne w powiecie dzierżoniowskim",
            "cpvCodes": ["45111200-0", "45246000-3"],
            "estimatedValue": 320000.0,
            "submissionDeadlineDate": "2024-04-10T12:00:00",
            "orderingPartyName": "Powiat Dzierżoniowski",
            "orderingPartyAddress": "Rynek 27, 58-200 Dzierżoniów",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
            "procedureType": "TP",
            "sourceKind": "bzp",
        }),
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00311200/01",
            "noticePublicationDate": "2024-03-22",
            "procurementObject": "Dostawa materiałów biurowych dla urzędu gminy",
            "cpvCodes": ["30192000-1"],  # OUT OF CPV SCOPE — should be filtered
            "estimatedValue": 45000.0,
            "submissionDeadlineDate": "2024-04-05T10:00:00",
            "orderingPartyName": "Gmina Bielawa",
            "orderingPartyAddress": "pl. Wolności 1, 58-260 Bielawa",
            "executionPlace": "dolnośląskie",
            "contractType": "D",  # Dostawa — not RC
            "procedureType": "TP",
            "sourceKind": "bzp",
        }),
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00320001/01",
            "noticePublicationDate": "2024-03-25",
            "procurementObject": "Budowa kanalizacji sanitarnej z robotami ziemnymi w Łagiewnikach",
            "cpvCodes": ["45232410-9", "45111200-0"],
            "estimatedValue": 1200000.0,
            "submissionDeadlineDate": "2024-04-20T10:00:00",
            "orderingPartyName": "Gmina Łagiewniki",
            "orderingPartyAddress": "ul. Jedności Narodowej 21, 58-210 Łagiewniki",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
            "procedureType": "TP",
            "sourceKind": "bzp",
        }),
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00400000/01",
            "noticePublicationDate": "2024-04-01",
            "procurementObject": "Roboty ziemne i drogowe — woj. mazowieckie",
            "cpvCodes": ["45111200-0", "45233120-6"],
            "estimatedValue": 500000.0,
            "submissionDeadlineDate": "2024-04-25T10:00:00",
            "orderingPartyName": "Gmina Pruszków",
            "orderingPartyAddress": "ul. Kraszewskiego 14/16, 05-800 Pruszków",
            "executionPlace": "mazowieckie",  # OUT OF GEO — for geo filter test
            "contractType": "RC",
            "procedureType": "TP",
            "sourceKind": "bzp",
        }),
        # ── Nowe fixtures — pełna branża budowlana ────────────────────────────
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00500001/01",
            "noticePublicationDate": "2024-05-10",
            "procurementObject": "Budowa budynku użyteczności publicznej — centrum kultury w Świdnicy",
            "cpvCodes": ["45210000-2", "45310000-3", "45330000-9"],
            "estimatedValue": 4200000.0,
            "submissionDeadlineDate": "2024-06-15T10:00:00",
            "orderingPartyName": "Gmina Świdnica",
            "orderingPartyAddress": "ul. Armii Krajowej 47, 58-100 Świdnica",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
            "procedureType": "TP",
            "sourceKind": "bzp",
        }),
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00500002/01",
            "noticePublicationDate": "2024-05-12",
            "procurementObject": "Przebudowa drogi gminnej nr 108012D w miejscowości Ziębice",
            "cpvCodes": ["45233120-6", "45233220-7"],
            "estimatedValue": 1100000.0,
            "submissionDeadlineDate": "2024-06-10T12:00:00",
            "orderingPartyName": "Gmina Ziębice",
            "orderingPartyAddress": "ul. Przemysłowa 10, 57-220 Ziębice",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
            "procedureType": "TP",
            "sourceKind": "bzp",
        }),
        BZPRawNotice({
            "noticeNumber": "2024/BZP 00500003/01",
            "noticePublicationDate": "2024-05-14",
            "procurementObject": "Budowa sieci kanalizacji sanitarnej i wodociągowej w Bielawie",
            "cpvCodes": ["45231300-8", "45232410-9", "45111200-0"],
            "estimatedValue": 2800000.0,
            "submissionDeadlineDate": "2024-06-20T10:00:00",
            "orderingPartyName": "Gmina Bielawa",
            "orderingPartyAddress": "pl. Wolności 1, 58-260 Bielawa",
            "executionPlace": "dolnośląskie",
            "contractType": "RC",
            "procedureType": "TP",
            "sourceKind": "bzp",
        }),
    ]
