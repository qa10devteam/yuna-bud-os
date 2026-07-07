"""Faza 42 — TED Integration: EU tenders from TED API (stub)."""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import uuid
from datetime import datetime, date

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/ted", tags=["ted-eu"])

TED_API_BASE = "https://api.ted.europa.eu/v3"


class TedSearchRequest(BaseModel):
    query: str = "construction works Poland"
    page: int = 1
    limit: int = 20
    country: str = "PL"


def _sync_ted(query: str, country: str, limit: int = 20) -> dict:
    """Fetch TED tenders and store in DB."""
    engine = get_engine()
    stored = 0
    errors = []
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{TED_API_BASE}/notices/search",
                json={
                    "query": f"ND=[*] AND TY=[3] AND CY=[{country}]",
                    "scope": "ACTIVE",
                    "fields": ["ND", "TI", "AU_NAME", "CY", "PC", "TV", "DT", "CW"],
                    "page": 1,
                    "pageSize": limit,
                    "sortField": "ND",
                    "sortOrder": "DESC",
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            notices = data.get("notices", [])
            for notice in notices:
                ted_id = notice.get("ND", str(uuid.uuid4()))
                with engine.connect() as conn:
                    conn.execute(
                        sa.text("""
                            INSERT INTO ted_tenders
                                (id, ted_id, title, buyer, country, cpv, value_eur, url, raw_json, published_at)
                            VALUES (:id, :ted_id, :title, :buyer, :country, :cpv, :value_eur, :url, :raw::jsonb, now())
                            ON CONFLICT (ted_id) DO UPDATE SET
                                title = EXCLUDED.title,
                                raw_json = EXCLUDED.raw_json
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "ted_id": ted_id,
                            "title": notice.get("TI", [{}])[0].get("value", "Unknown") if isinstance(notice.get("TI"), list) else str(notice.get("TI", "")),
                            "buyer": notice.get("AU_NAME", ""),
                            "country": country,
                            "cpv": notice.get("PC", []),
                            "value_eur": float(notice.get("TV", 0)) if notice.get("TV") else None,
                            "url": f"https://ted.europa.eu/udl?uri=TED:NOTICE:{ted_id}:DATA:EN:HTML",
                            "raw": __import__("json").dumps(notice),
                        },
                    )
                    conn.commit()
                stored += 1
    except Exception as exc:
        errors.append(str(exc))
        # Store sample stub entry on API failure
        with engine.connect() as conn:
            stub_id = f"TED-STUB-{date.today().isoformat()}"
            conn.execute(
                sa.text("""
                    INSERT INTO ted_tenders (id, ted_id, title, buyer, country, cpv, url, published_at)
                    VALUES (:id, :ted_id, :title, :buyer, :country, :cpv, :url, now())
                    ON CONFLICT (ted_id) DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "ted_id": stub_id,
                    "title": f"Roboty ziemne i budowlane — EU stub ({date.today()})",
                    "buyer": "European Authority (stub)",
                    "country": country,
                    "cpv": ["45000000", "45100000"],
                    "url": "https://ted.europa.eu",
                },
            )
            conn.commit()
    return {"stored": stored, "errors": errors}


@router.post("/sync")
def ted_sync(
    background_tasks: BackgroundTasks,
    user: AuthUser,
    country: str = Query("PL"),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Synchronizuj przetargi EU z TED API."""
    background_tasks.add_task(_sync_ted, "construction building works", country, limit)
    return {
        "status": "started",
        "country": country,
        "message": f"Synchronizacja TED uruchomiona dla kraju: {country}",
    }


@router.get("")
def list_ted_tenders(
    user: AuthUser,
    country: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Lista przetargów EU z TED."""
    engine = get_engine()
    filters = ""
    params: dict = {"limit": limit, "offset": offset}
    if country:
        filters = "WHERE country = :country"
        params["country"] = country
    with engine.connect() as conn:
        total = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM ted_tenders {filters}"), params
        ).scalar()
        rows = conn.execute(
            sa.text(f"""
                SELECT id, ted_id, title, buyer, country, cpv, value_eur, url, published_at, created_at
                FROM ted_tenders {filters}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).fetchall()
    return {
        "total": int(total or 0),
        "items": [
            {
                "id": str(r.id),
                "ted_id": r.ted_id,
                "title": r.title,
                "buyer": r.buyer,
                "country": r.country,
                "cpv": list(r.cpv) if r.cpv else [],
                "value_eur": float(r.value_eur) if r.value_eur else None,
                "url": r.url,
                "published_at": r.published_at.isoformat() if r.published_at else None,
            }
            for r in rows
        ],
    }


@router.get("/{ted_id}")
def get_ted_tender(ted_id: str, user: AuthUser) -> dict:
    """Szczegóły przetargu EU z TED."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT * FROM ted_tenders WHERE id = :id OR ted_id = :tid"),
            {"id": ted_id, "tid": ted_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Przetarg TED nie istnieje")
    return {
        "id": str(row.id),
        "ted_id": row.ted_id,
        "title": row.title,
        "buyer": row.buyer,
        "country": row.country,
        "cpv": list(row.cpv) if row.cpv else [],
        "value_eur": float(row.value_eur) if row.value_eur else None,
        "url": row.url,
        "raw_json": row.raw_json,
        "published_at": row.published_at.isoformat() if row.published_at else None,
    }
