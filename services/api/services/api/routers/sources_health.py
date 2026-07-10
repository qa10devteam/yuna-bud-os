"""Sources health check — liveness status of BZP and TED APIs + DB ingest stats.

S24/S25: Extended with {source, status, latency_ms, last_ok_at} format and
source_down notifications when latency > 5000ms.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["sources"])

BZP_PROBE_URL = "https://api.ezamowienia.gov.pl/mo-board/api/v1/notice"
TED_PROBE_URL = "https://api.ted.europa.eu/v3/notices/search"
BIP_PROBE_URL = "https://aplikacje.gov.pl/app/bip-back/api/subjects"

# S24/S25: HEAD probe URLs (lighter than full GET)
BZP_HEAD_URL = "https://ezamowienia.gov.pl"
TED_HEAD_URL = "https://ted.europa.eu"
BIP_HEAD_URL = "https://aplikacje.gov.pl"

_TIMEOUT = 8.0
_LATENCY_WARN_MS = 5000  # S24/S25: threshold for source_down notification


class SourceStatus(BaseModel):
    name: str
    status: str          # "ok" | "degraded" | "error"
    latency_ms: int | None = None
    last_ok_at: str | None = None
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


def _probe_head(name: str, url: str) -> SourceStatus:
    """HEAD ping — returns latency_ms and ok status."""
    t0 = time.monotonic()
    try:
        resp = httpx.head(url, timeout=5.0, follow_redirects=True)
        latency = int((time.monotonic() - t0) * 1000)
        last_ok_at = datetime.now(tz=timezone.utc).isoformat()
        if resp.status_code in (200, 301, 302, 403):
            status = "ok" if latency < _LATENCY_WARN_MS else "degraded"
            return SourceStatus(name=name, status=status, latency_ms=latency, last_ok_at=last_ok_at)
        return SourceStatus(
            name=name, status="degraded",
            latency_ms=latency, last_ok_at=last_ok_at,
            detail=f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        return SourceStatus(name=name, status="error", detail=str(exc)[:120])


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
        last_ok_at = datetime.now(tz=timezone.utc).isoformat()
        if resp.status_code == 200:
            return SourceStatus(name="BZP", status="ok", latency_ms=latency, last_ok_at=last_ok_at)
        return SourceStatus(
            name="BZP", status="degraded",
            latency_ms=latency, last_ok_at=last_ok_at,
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
        last_ok_at = datetime.now(tz=timezone.utc).isoformat()
        if resp.status_code == 200:
            total = resp.json().get("totalNoticeCount", 0)
            return SourceStatus(
                name="TED", status="ok", latency_ms=latency, last_ok_at=last_ok_at,
                detail=f"totalNoticeCount={total}",
            )
        return SourceStatus(
            name="TED", status="degraded",
            latency_ms=latency, last_ok_at=last_ok_at,
            detail=f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        return SourceStatus(name="TED", status="error", detail=str(exc)[:120])


def _insert_source_down_notification(tenant_id: str, source_name: str) -> None:
    """S24/S25: Insert source_down notification when latency > threshold."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO notifications (tenant_id, type, title, created_at)
                VALUES (:tid, 'source_down', :title, now())
            """), {
                "tid": tenant_id,
                "title": f"Źródło {source_name} niedostępne",
            })
    except Exception:
        pass  # non-critical


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
    import asyncio

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


@router.get("/api/v2/sources/health", response_model=SourcesHealthResponse)
async def sources_health_v2() -> dict:
    """S24/S25: Extended sources health with latency_ms + last_ok_at per source.

    Returns list of {source, status, latency_ms, last_ok_at}.
    Inserts source_down notification if latency > 5000ms.
    """
    import asyncio

    tenant_id = os.getenv("DEFAULT_TENANT_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")
    loop = asyncio.get_event_loop()

    bzp_s, ted_s, bip_s = await asyncio.gather(
        loop.run_in_executor(None, _probe_head, "BZP", BZP_HEAD_URL),
        loop.run_in_executor(None, _probe_head, "TED", TED_HEAD_URL),
        loop.run_in_executor(None, _probe_head, "BIP", BIP_HEAD_URL),
    )

    results = []
    for src in (bzp_s, ted_s, bip_s):
        # S24/S25: notify if latency too high or error
        if src.status in ("error", "degraded") or (src.latency_ms is not None and src.latency_ms >= _LATENCY_WARN_MS):
            loop.run_in_executor(None, _insert_source_down_notification, tenant_id, src.name)
        results.append({
            "source": src.name,
            "status": src.status,
            "latency_ms": src.latency_ms,
            "last_ok_at": src.last_ok_at,
        })

    return {
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        "sources": results,
    }

