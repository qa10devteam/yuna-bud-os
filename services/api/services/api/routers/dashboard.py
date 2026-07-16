"""
Dashboard router — statystyki ogólne dla użytkownika.

Endpoints:
    GET  /api/v1/dashboard                   — statystyki dla panelu głównego (v1)
    GET  /api/v2/dashboard/stats             — statystyki dla panelu głównego (v2)
    GET  /api/v2/dashboard/digest            — pobierz ostatni AI digest (cache 8h)
    POST /api/v2/dashboard/digest/generate   — generuj nowy AI digest via vLLM
    GET  /api/v2/dashboard/pipeline-kpi      — KPI z mv_pipeline_kpi

S4-1 fix: all stats in a single CTE query (was 7 separate SELECTs → N+1).
S4-4 fix: in-process TTL cache 60s per org_id.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from terra_db.session import get_engine
from ..auth.deps import AuthUser
from ..cache import get as cache_get, set as cache_set

router = APIRouter(tags=["dashboard"])
logger = logging.getLogger(__name__)

_CACHE_TTL = 60  # seconds


def _get_dashboard_data(tenant_id: str) -> dict:
    """Single-query dashboard stats via CTE — no N+1."""
    engine = get_engine()
    with engine.connect() as conn:
        # ── One CTE for all scalar aggregates ─────────────────────────────────
        agg = conn.execute(sa.text("""
            SELECT
                COUNT(*)                                                   AS total_tenders,
                COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE)   AS new_today,
                COUNT(*) FILTER (WHERE match_score > 0.6)                 AS high_score_count,
                ROUND(AVG(match_score)::numeric, 4)                       AS avg_score,
                COALESCE(SUM(value_pln) FILTER (WHERE value_pln IS NOT NULL), 0) AS pipeline_value,
                COUNT(DISTINCT buyer) FILTER (WHERE buyer IS NOT NULL)    AS unique_buyers
            FROM tender
            WHERE duplicate_of IS NULL
              AND tenant_id = :tid
        """), {"tid": tenant_id}).fetchone()

        total_tenders   = int(agg.total_tenders)   if agg else 0
        new_today       = int(agg.new_today)        if agg else 0
        high_score_count= int(agg.high_score_count) if agg else 0
        avg_score       = float(agg.avg_score)      if agg and agg.avg_score else None
        pipeline_value  = float(agg.pipeline_value) if agg else 0.0
        unique_buyers   = int(agg.unique_buyers)    if agg else 0

        # ── by_source (single GROUP BY) ───────────────────────────────────────
        source_rows = conn.execute(sa.text("""
            SELECT source::text, COUNT(*)
            FROM tender
            WHERE duplicate_of IS NULL AND tenant_id = :tid
            GROUP BY source
        """), {"tid": tenant_id}).fetchall()
        by_source = {r[0]: int(r[1]) for r in source_rows if r[0]}

        # ── weekly_activity (last 7 days, count per day) ─────────────────────
        activity_rows = conn.execute(sa.text("""
            SELECT d.day, COALESCE(sub.c, 0) AS cnt
            FROM (SELECT generate_series(CURRENT_DATE - 6, CURRENT_DATE, '1 day'::interval)::date AS day) d
            LEFT JOIN (
                SELECT DATE(created_at) AS dt, COUNT(*) AS c
                FROM tender
                WHERE duplicate_of IS NULL
                  AND tenant_id = :tid
                  AND created_at >= CURRENT_DATE - 6
                GROUP BY DATE(created_at)
            ) sub ON sub.dt = d.day
            ORDER BY d.day
        """), {"tid": tenant_id}).fetchall()
        weekly_activity = [{"day": str(r.day), "count": int(r.cnt)} for r in activity_rows]
        new_this_week = sum(r.cnt for r in activity_rows)

        # ── top-5 by match_score ───────────────────────────────────────────────
        top_rows = conn.execute(sa.text("""
            SELECT id, title, source::text, value_pln, match_score, status::text
            FROM tender
            WHERE duplicate_of IS NULL
              AND match_score IS NOT NULL
              AND tenant_id = :tid
            ORDER BY match_score DESC
            LIMIT 5
        """), {"tid": tenant_id}).fetchall()
        top_tenders = [
            {
                "id": str(r.id),
                "title": r.title,
                "source": r.source,
                "value_pln": float(r.value_pln) if r.value_pln is not None else None,
                "match_score": float(r.match_score) if r.match_score is not None else None,
                "status": r.status,
            }
            for r in top_rows
        ]

    return {
        "total_tenders": total_tenders,
        "new_today": new_today,
        "new_this_week": new_this_week,
        "high_score_count": high_score_count,
        "by_source": by_source,
        "top_tenders": top_tenders,
        "avg_score": avg_score,
        "pipeline_value": pipeline_value,
        "unique_buyers": unique_buyers,
        "weekly_activity": weekly_activity,
    }


def _cached_dashboard(tenant_id: str) -> dict:
    """Return cached or fresh dashboard data (60s TTL)."""
    cache_key = f"dashboard:{tenant_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    data = _get_dashboard_data(tenant_id)
    cache_set(cache_key, data, ttl=_CACHE_TTL)
    return data


@router.get("/api/v1/dashboard")
def dashboard_stats_v1(user: AuthUser) -> dict:
    """Panel główny — statystyki przetargów (v1)."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    return _cached_dashboard(tenant_id)


@router.get("/api/v2/dashboard/stats")
def dashboard_stats_v2(user: AuthUser) -> dict:
    """Panel główny — statystyki przetargów (v2)."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    return _cached_dashboard(tenant_id)


@router.get("/api/v2/dashboard")
def dashboard_kpi_root(user: AuthUser) -> dict:
    """Root dashboard KPI — active_tenders, pipeline_value, win_rate_mtd, avg_deal_size, new_today."""
    kpi = get_pipeline_kpi(user)
    # Map active_count → active_tenders for frontend compatibility
    return {
        "active_tenders": kpi.get("active_count", 0),
        "pipeline_value": kpi.get("pipeline_value", 0),
        "win_rate_mtd": kpi.get("win_rate_mtd", 0),
        "avg_deal_size": kpi.get("avg_deal_size", 0),
        "new_today": kpi.get("new_today", 0),
    }


# ── Dashboard Digest (AI-generated) ──────────────────────────────────────────

@router.get("/api/v2/dashboard/digest")
def get_dashboard_digest(user: AuthUser) -> dict:
    """Return cached AI digest if generated within the last 8 hours."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT detail, created_at
            FROM audit_log
            WHERE action = 'dashboard_digest'
              AND tenant_id = :tid
            ORDER BY created_at DESC
            LIMIT 1
        """), {"tid": tenant_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No digest available")

    details = row[0] if isinstance(row[0], dict) else (json.loads(row[0]) if row[0] else {})
    generated_at = row[1]

    # Check freshness: must be within the last 8 hours
    if generated_at is not None:
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - generated_at).total_seconds() / 3600
        if age_hours > 8:
            raise HTTPException(status_code=404, detail="Digest expired — please regenerate")
    else:
        raise HTTPException(status_code=404, detail="No digest available")

    content = details.get("content", "")
    return {"content": content, "generated_at": generated_at.isoformat()}


@router.post("/api/v2/dashboard/digest/generate")
def generate_dashboard_digest(user: AuthUser) -> dict:
    """Generate a new AI digest via vLLM and persist it to audit_log."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    vllm_base = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8001/v1")

    # Gather context: KPI stats + top tenders
    data = _get_dashboard_data(tenant_id)
    top_tenders_summary = "\n".join(
        f"- {t['title']} (score: {t['match_score']}, wartość: {t['value_pln']} PLN)"
        for t in data.get("top_tenders", [])
    ) or "Brak przetargów."

    user_prompt = (
        f"Statystyki pipeline (KPI):\n"
        f"- Łącznie przetargów: {data.get('total_tenders', 0)}\n"
        f"- Nowe dzisiaj: {data.get('new_today', 0)}\n"
        f"- Wysoki wynik dopasowania (>60%): {data.get('high_score_count', 0)}\n"
        f"- Wartość pipeline: {data.get('pipeline_value', 0):.0f} PLN\n"
        f"- Średni score: {data.get('avg_score') or 'N/A'}\n\n"
        f"Top 5 przetargów wg dopasowania:\n{top_tenders_summary}\n\n"
        "Na podstawie powyższych danych wygeneruj dzienny digest w języku polskim "
        "w formacie Markdown (200-300 słów). Podsumuj aktywność, wyróżnij szanse "
        "i zaproponuj działania na dziś."
    )

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{vllm_base}/chat/completions",
                json={
                    "model": "axon",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Jesteś budos — AI asystentem do przetargów budowlanych.",
                        },
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("vLLM digest generation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"vLLM unavailable: {exc}") from exc

    now = datetime.now(timezone.utc)
    details_json = json.dumps({"content": content})

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO audit_log (tenant_id, user_id, action, entity_type, detail, created_at)
            VALUES (:tid, 'system', 'dashboard_digest', 'dashboard', CAST(:details AS jsonb), NOW())
        """), {"tid": tenant_id, "details": details_json})

    return {"content": content, "generated_at": now.isoformat()}


# ── Pipeline KPI ──────────────────────────────────────────────────────────────

@router.get("/api/v2/dashboard/pipeline-kpi")
def get_pipeline_kpi(user: AuthUser) -> dict:
    """Return KPI from mv_pipeline_kpi; falls back to inline calculation."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    engine = get_engine()
    with engine.connect() as conn:
        # Try materialised view first
        try:
            row = conn.execute(sa.text("""
                SELECT active_count, pipeline_value, win_rate_mtd, avg_deal_size, new_today
                FROM mv_pipeline_kpi
                WHERE tenant_id = :tid
                LIMIT 1
            """), {"tid": tenant_id}).fetchone()
            if row:
                return {
                    "active_count": int(row.active_count) if row.active_count is not None else 0,
                    "pipeline_value": float(row.pipeline_value) if row.pipeline_value is not None else 0.0,
                    "win_rate_mtd": float(row.win_rate_mtd) if row.win_rate_mtd is not None else None,
                    "avg_deal_size": float(row.avg_deal_size) if row.avg_deal_size is not None else None,
                    "new_today": int(row.new_today) if row.new_today is not None else 0,
                    "source": "mv_pipeline_kpi",
                }
        except Exception:
            pass  # mv doesn't exist — fall through to inline

        # Inline fallback from tender table
        agg = conn.execute(sa.text("""
            SELECT
                COUNT(*) FILTER (WHERE status NOT IN ('archived', 'rejected', 'lost'))
                                                        AS active_count,
                COALESCE(SUM(value_pln) FILTER (
                    WHERE value_pln IS NOT NULL
                      AND status NOT IN ('archived', 'rejected', 'lost')
                ), 0)                                   AS pipeline_value,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE status = 'won'
                        AND DATE_TRUNC('month', updated_at) = DATE_TRUNC('month', NOW()))
                    / NULLIF(COUNT(*) FILTER (
                        WHERE DATE_TRUNC('month', updated_at) = DATE_TRUNC('month', NOW())
                    ), 0), 2
                )                                       AS win_rate_mtd,
                ROUND(AVG(value_pln) FILTER (WHERE value_pln IS NOT NULL)::numeric, 2)
                                                        AS avg_deal_size,
                COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE)
                                                        AS new_today
            FROM tender
            WHERE duplicate_of IS NULL
              AND tenant_id = :tid
        """), {"tid": tenant_id}).fetchone()

    return {
        "active_count": int(agg.active_count) if agg and agg.active_count is not None else 0,
        "pipeline_value": float(agg.pipeline_value) if agg else 0.0,
        "win_rate_mtd": float(agg.win_rate_mtd) if agg and agg.win_rate_mtd is not None else None,
        "avg_deal_size": float(agg.avg_deal_size) if agg and agg.avg_deal_size is not None else None,
        "new_today": int(agg.new_today) if agg and agg.new_today is not None else 0,
        "source": "tender_inline",
    }
