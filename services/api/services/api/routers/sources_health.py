"""Sources health check — liveness status of BZP and TED APIs + DB ingest stats."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["sources"])

BZP_PROBE_URL = "https://api.ezamowienia.gov.pl/mo-board/api/v1/notice"
TED_PROBE_URL = "https://api.ted.europa.eu/v3/notices/search"

_TIMEOUT = 8.0


class SourceStatus(BaseModel):
    name: str
    status: str          # "ok" | "degraded" | "error"
    latency_ms: int | None = None
    detail: str | None = None


class IngestStats(BaseModel):
    total_tenders: int
    bzp_count: int
    ted_count: int
    bip_count: int = 0
    duplicate_pairs: int = 0
    last_published: str | None = None   # ISO datetime of newest tender


class SourcesHealthResponse(BaseModel):
    status: str          # "ok" | "degraded" | "error"
    checked_at: str      # ISO datetime
    sources: list[SourceStatus]
    ingest: IngestStats


def _probe_bzp() -> SourceStatus:
    """Ping BZP API with a minimal query (pageSize=1)."""
    t0 = time.monotonic()
    try:
        resp = httpx.get(
            BZP_PROBE_URL,
            params={"pageSize": 1, "pageNumber": 0, "NoticeType": "ContractNotice"},
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        latency = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            return SourceStatus(name="BZP", status="ok", latency_ms=latency)
        return SourceStatus(
            name="BZP", status="degraded",
            latency_ms=latency,
            detail=f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        return SourceStatus(name="BZP", status="error", detail=str(exc)[:120])


def _probe_ted() -> SourceStatus:
    """Ping TED v3 API with a minimal query."""
    t0 = time.monotonic()
    try:
        resp = httpx.post(
            TED_PROBE_URL,
            json={
                "query": "organisation-country-buyer=POL AND contract-nature=works",
                "fields": ["publication-number"],
                "limit": 1,
            },
            timeout=_TIMEOUT,
        )
        latency = int((time.monotonic() - t0) * 1000)
        if resp.status_code == 200:
            total = resp.json().get("totalNoticeCount", 0)
            return SourceStatus(
                name="TED", status="ok", latency_ms=latency,
                detail=f"totalNoticeCount={total}",
            )
        return SourceStatus(
            name="TED", status="degraded",
            latency_ms=latency,
            detail=f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        return SourceStatus(name="TED", status="error", detail=str(exc)[:120])


def _get_ingest_stats(tenant_id: str) -> IngestStats:
    """Query DB for tender counts per source."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT source, COUNT(*) as cnt
                FROM tender
                WHERE tenant_id = :tid
                GROUP BY source
            """), {"tid": tenant_id})
            rows = {r.source: r.cnt for r in result}

            newest = conn.execute(text("""
                SELECT MAX(published_at) FROM tender WHERE tenant_id = :tid
            """), {"tid": tenant_id}).scalar()

        from sqlalchemy import text as sa_text
        return IngestStats(
            total_tenders=sum(rows.values()),
            bzp_count=rows.get("bzp", 0),
            ted_count=rows.get("ted", 0),
            bip_count=rows.get("bip", 0),
            duplicate_pairs=int(conn.execute(sa_text(
                "SELECT COUNT(*) FROM tender_duplicate WHERE tenant_id = :tid"
            ), {"tid": tenant_id}).scalar() or 0),
            last_published=newest.isoformat() if newest else None,
        )
    except Exception:
        return IngestStats(total_tenders=0, bzp_count=0, ted_count=0)


@router.get("/api/v1/sources/health", response_model=SourcesHealthResponse)
async def sources_health() -> SourcesHealthResponse:
    """Live health check of BZP and TED data sources + ingest stats from DB."""
    import os, asyncio

    tenant_id = os.getenv("DEFAULT_TENANT_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")

    # Probe both APIs concurrently (run in threadpool since httpx is sync here)
    loop = asyncio.get_event_loop()
    bzp_status, ted_status, stats = await asyncio.gather(
        loop.run_in_executor(None, _probe_bzp),
        loop.run_in_executor(None, _probe_ted),
        loop.run_in_executor(None, _get_ingest_stats, tenant_id),
    )

    sources = [bzp_status, ted_status]
    any_error = any(s.status == "error" for s in sources)
    any_degraded = any(s.status == "degraded" for s in sources)
    overall = "error" if any_error else ("degraded" if any_degraded else "ok")

    return SourcesHealthResponse(
        status=overall,
        checked_at=datetime.now(tz=timezone.utc).isoformat(),
        sources=sources,
        ingest=stats,
    )
