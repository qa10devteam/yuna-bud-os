"""S3 — UZP Change Tracker router.

Endpointy:
- GET /api/v2/uzp/changes  — lista zmian z uzp_changes
- GET /api/v2/uzp/summary  — AI summary ostatnich 7 dni
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/uzp", tags=["uzp-tracker"])

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-20250514-v1:0")


# ─── Pydantic models ──────────────────────────────────────────────────────────

class UZPChangeItem(BaseModel):
    id: str
    source: str
    title: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    severity: str = "info"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UZPChangesResponse(BaseModel):
    items: list[UZPChangeItem]
    total: int
    limit: int
    offset: int


class UZPSummaryResponse(BaseModel):
    summary: str
    period_days: int
    records_count: int
    generated_at: datetime
    source: str  # 'ai' | 'fallback' | 'empty'


# ─── Helper: sprawdź czy tabela istnieje ─────────────────────────────────────

def _table_exists(conn: sa.Connection) -> bool:
    try:
        result = conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'uzp_changes')"
            )
        )
        return bool(result.scalar())
    except Exception:
        return False


# ─── GET /api/v2/uzp/changes ─────────────────────────────────────────────────

@router.get("/changes", response_model=UZPChangesResponse)
def get_uzp_changes(
    user: AuthUser,
    source: Optional[str] = Query(None, description="Filtruj po źródle: uzp_news | uzp_plans | ezamowienia"),
    severity: Optional[str] = Query(None, description="Filtruj po ważności: critical | high | info"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> UZPChangesResponse:
    """Lista zmian UZP posortowana od najnowszych."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            if not _table_exists(conn):
                return UZPChangesResponse(items=[], total=0, limit=limit, offset=offset)

            # Buduj zapytanie
            where_parts = []
            params: dict = {}

            if source:
                where_parts.append("source = :source")
                params["source"] = source
            if severity:
                where_parts.append("severity = :severity")
                params["severity"] = severity

            where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

            # Count
            total_row = conn.execute(
                sa.text(f"SELECT COUNT(*) FROM uzp_changes {where_clause}"),
                params,
            ).scalar() or 0

            # Fetch
            rows = conn.execute(
                sa.text(
                    f"""
                    SELECT id, source, title, url, published_at,
                           summary, category, severity, created_at
                    FROM uzp_changes
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {**params, "limit": limit, "offset": offset},
            ).fetchall()

            items = [
                UZPChangeItem(
                    id=str(row[0]),
                    source=row[1],
                    title=row[2],
                    url=row[3],
                    published_at=row[4],
                    summary=row[5],
                    category=row[6],
                    severity=row[7] or "info",
                    created_at=row[8],
                )
                for row in rows
            ]

            return UZPChangesResponse(
                items=items,
                total=int(total_row),
                limit=limit,
                offset=offset,
            )

    except Exception as e:
        logger.error("Błąd GET /api/v2/uzp/changes: %s", e)
        return UZPChangesResponse(items=[], total=0, limit=limit, offset=offset)


# ─── GET /api/v2/uzp/summary ─────────────────────────────────────────────────

@router.get("/summary", response_model=UZPSummaryResponse)
def get_uzp_summary(user: AuthUser) -> UZPSummaryResponse:
    """AI summary ostatnich 7 dni zmian UZP."""
    now = datetime.now(timezone.utc)
    period_days = 7

    # Pobierz ostatnie rekordy z DB
    try:
        engine = get_engine()
        with engine.connect() as conn:
            if not _table_exists(conn):
                return UZPSummaryResponse(
                    summary="Brak danych — tabela uzp_changes nie istnieje. Uruchom najpierw skrypt uzp_tracker.py.",
                    period_days=period_days,
                    records_count=0,
                    generated_at=now,
                    source="empty",
                )

            rows = conn.execute(
                sa.text(
                    """
                    SELECT source, title, category, severity, created_at
                    FROM uzp_changes
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    ORDER BY severity DESC, created_at DESC
                    LIMIT 50
                    """
                )
            ).fetchall()

            records_count = len(rows)

            if records_count == 0:
                return UZPSummaryResponse(
                    summary=(
                        "Brak danych z ostatnich 7 dni. "
                        "Uruchom skrypt uzp_tracker.py aby pobrać aktualne zmiany."
                    ),
                    period_days=period_days,
                    records_count=0,
                    generated_at=now,
                    source="empty",
                )

            # Zbuduj listę zmian do promptu
            items_text = "\n".join(
                f"- [{row[3] or 'info'}][{row[0]}] {row[1]}"
                for row in rows[:30]
            )

    except Exception as e:
        logger.error("Błąd odczytu uzp_changes: %s", e)
        return UZPSummaryResponse(
            summary="Błąd odczytu danych — sprawdź logi serwera.",
            period_days=period_days,
            records_count=0,
            generated_at=now,
            source="fallback",
        )

    # Wywołaj Bedrock
    try:
        import boto3

        prompt = (
            f"Jesteś ekspertem ds. polskiego prawa zamówień publicznych.\n\n"
            f"Na podstawie poniższych pozycji z ostatnich {period_days} dni, "
            f"streść najważniejsze zmiany w polskim prawie zamówień publicznych. "
            f"Bądź konkretny i wskaż co to oznacza dla wykonawców.\n\n"
            f"Pozycje:\n{items_text}\n\n"
            f"Odpowiedz w języku polskim, max 3 akapity."
        )

        bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }),
            contentType="application/json",
            accept="application/json",
        )
        ai_text = json.loads(response["body"].read())["content"][0]["text"]

        return UZPSummaryResponse(
            summary=ai_text,
            period_days=period_days,
            records_count=records_count,
            generated_at=now,
            source="ai",
        )

    except Exception as e:
        logger.warning("Bedrock niedostępny dla /uzp/summary: %s", e)

        # Fallback: prosty summary bez AI
        sources_set = sorted(set(row[0] for row in rows))
        high_items = [row[1] for row in rows if row[3] in ("critical", "high")]

        fallback_lines = [
            f"W ciągu ostatnich {period_days} dni zarejestrowano {records_count} zmian "
            f"ze źródeł: {', '.join(sources_set)}.",
        ]
        if high_items:
            fallback_lines.append(
                f"Ważne pozycje: " + "; ".join(high_items[:3]) + "."
            )
        fallback_lines.append(
            "Szczegółowe dane dostępne przez endpoint /api/v2/uzp/changes. "
            "(AI summary niedostępne — Bedrock tymczasowo wyłączony)"
        )

        return UZPSummaryResponse(
            summary=" ".join(fallback_lines),
            period_days=period_days,
            records_count=records_count,
            generated_at=now,
            source="fallback",
        )
