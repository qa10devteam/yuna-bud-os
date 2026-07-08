"""M1 — Ingestion repository: upserts TenderIn into DB (idempotent)."""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.engine import Engine

from .normalize import TenderIn

logger = logging.getLogger(__name__)


def upsert_tender(
    engine: Engine,
    tender: TenderIn,
    *,
    match_score: float,
    match_reason: str,
    tenant_id: str,
) -> tuple[str, bool]:
    """Upsert tender. Returns (tender_id, created: bool). Idempotent."""
    now = datetime.now(timezone.utc)
    raw_json = json.dumps(tender.raw, ensure_ascii=False, default=str)

    with engine.begin() as conn:
        row = conn.execute(
            sa.text(
                "SELECT id FROM tender "
                "WHERE tenant_id = :tenant_id AND source = :source AND external_id = :ext_id"
            ),
            {"tenant_id": tenant_id, "source": tender.source, "ext_id": tender.external_id},
        ).fetchone()

        if row:
            # UPDATE — avoid ::cast by using sa.cast via raw SQL with ARRAY literal
            conn.execute(
                sa.text(
                    "UPDATE tender SET "
                    "  title=:title, buyer=:buyer, voivodeship=:voivodeship, "
                    "  nuts_code=:nuts_code, "
                    "  value_pln=:value_pln, deadline_at=:deadline_at, "
                    "  published_at=:published_at, url=:url, "
                    "  match_score=:match_score, match_reason=:match_reason, "
                    "  raw=cast(:raw as jsonb), cpv=cast(:cpv as text[]) "
                    "WHERE id=:id"
                ),
                {
                    "id": str(row[0]),
                    "title": tender.title,
                    "buyer": tender.buyer,
                    "voivodeship": tender.voivodeship,
                    "nuts_code": getattr(tender, "nuts_code", None),
                    "value_pln": float(tender.value_pln) if tender.value_pln else None,
                    "deadline_at": tender.deadline_at,
                    "published_at": tender.published_at,
                    "url": tender.url,
                    "match_score": match_score,
                    "match_reason": match_reason,
                    "raw": raw_json,
                    "cpv": "{" + ",".join(tender.cpv) + "}",
                },
            )
            return str(row[0]), False

        new_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO tender "
                "(id, tenant_id, source, external_id, title, buyer, cpv, "
                " voivodeship, nuts_code, value_pln, deadline_at, published_at, url, "
                " status, match_score, match_reason, raw, created_at) "
                "VALUES "
                "(:id, :tenant_id, :source, :ext_id, :title, :buyer, cast(:cpv as text[]), "
                " :voivodeship, :nuts_code, :value_pln, :deadline_at, :published_at, :url, "
                " cast(:status as tender_status), :match_score, :match_reason, "
                " cast(:raw as jsonb), :created_at)"
            ),
            {
                "id": new_id,
                "tenant_id": tenant_id,
                "source": tender.source,
                "ext_id": tender.external_id,
                "title": tender.title,
                "buyer": tender.buyer,
                "cpv": "{" + ",".join(tender.cpv) + "}",
                "voivodeship": tender.voivodeship,
                "nuts_code": getattr(tender, "nuts_code", None),
                "value_pln": float(tender.value_pln) if tender.value_pln else None,
                "deadline_at": tender.deadline_at,
                "published_at": tender.published_at,
                "url": tender.url,
                "status": "new",
                "match_score": match_score,
                "match_reason": match_reason,
                "raw": raw_json,
                "created_at": now,
            },
        )
        return new_id, True


def get_or_create_default_tenant(engine: Engine) -> str:
    """Return the default tenant ID for ingestion.

    Priority:
    1. DEFAULT_TENANT_ID env var (used in tests / CI to pin a specific org)
    2. First tenant in the `tenant` table ordered by created_at
    3. Create a new tenant row if the table is empty
    """
    pinned = os.getenv("DEFAULT_TENANT_ID")
    if pinned:
        return pinned

    with engine.begin() as conn:
        row = conn.execute(
            sa.text("SELECT id FROM tenant ORDER BY created_at LIMIT 1")
        ).fetchone()
        if row:
            return str(row[0])
        new_id = str(uuid.uuid4())
        conn.execute(
            sa.text("INSERT INTO tenant (id, name, created_at) VALUES (:id, :name, now())"),
            {"id": new_id, "name": "Default Tenant"},
        )
        return new_id

