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


@router.get("/api/v2/dashboard/market-charts")
def get_market_charts(user: AuthUser) -> dict:
    """S6 — dane do wykresów Market Dashboard (BZP + TED + GUS).

    Zwraca:
    - kpi: KPI nagłówkowe (liczby na top-bar)
    - bzp_weekly: trend tygodniowy 26 tyg (AreaChart)
    - ted_types: podział notice_type (PieChart)
    - ted_cpv: top 10 CPV w TED (HorizontalBar)
    - gus_production: produkcja budowlana top-5 woj (MultiLine)
    - gus_wages: wynagrodzenia w budownictwie (AreaChart)
    - bzp_cpv: top 10 CPV w BZP (HorizontalBar)
    - bzp_voivodeship: rozkład wg NUTS2 (PolandHeatmap)
    - pretender_monthly: pre-tender sygnały wg miesiąca (BarChart)
    """
    engine = get_engine()
    with engine.connect() as conn:

        # ── 0. KPI header ────────────────────────────────────────────────────
        bzp_kpi = conn.execute(sa.text("""
            SELECT
                COUNT(*)                                              AS bzp_30d,
                COUNT(DISTINCT contractor_nip)                        AS unique_contractors,
                ROUND(AVG(awarded_value)::numeric / 1000, 1)         AS avg_value_k,
                ROUND(SUM(awarded_value)::numeric / 1e9, 2)          AS total_value_bln
            FROM bzp_results
            WHERE publication_date >= NOW() - INTERVAL '30 days'
              AND awarded_value IS NOT NULL
        """)).fetchone()

        ted_kpi = conn.execute(sa.text("""
            SELECT COUNT(*) AS ted_30d
            FROM ted_notices
            WHERE publication_date >= NOW() - INTERVAL '30 days'
        """)).fetchone()

        pretender_kpi = conn.execute(sa.text("""
            SELECT COUNT(*) AS pretender_30d
            FROM pretender_signals
            WHERE published_at >= NOW() - INTERVAL '30 days'
        """)).fetchone()

        gus_latest = conn.execute(sa.text("""
            SELECT ROUND(AVG(value)::numeric / 1e6, 1) AS avg_production_mln
            FROM gus_indicators
            WHERE variable_name ILIKE '%produkcja%'
              AND year = (SELECT MAX(year) FROM gus_indicators WHERE variable_name ILIKE '%produkcja%')
        """)).fetchone()

        # ── 1. BZP — trend tygodniowy 26 tyg ────────────────────────────────
        bzp_weekly = conn.execute(sa.text("""
            SELECT
                TO_CHAR(DATE_TRUNC('week', publication_date), 'YYYY-MM-DD') AS week,
                COUNT(*)                                                      AS count
            FROM bzp_results
            WHERE publication_date >= NOW() - INTERVAL '182 days'
            GROUP BY DATE_TRUNC('week', publication_date)
            ORDER BY week ASC
        """)).fetchall()

        # ── 2. TED — podział notice_type ─────────────────────────────────────
        ted_types = conn.execute(sa.text("""
            SELECT notice_type, COUNT(*) AS count
            FROM ted_notices
            WHERE notice_type IS NOT NULL
            GROUP BY notice_type
            ORDER BY count DESC
        """)).fetchall()

        # ── 3. TED — top 10 CPV (2-cyfrowy prefix dla czytelności) ──────────
        ted_cpv = conn.execute(sa.text("""
            SELECT
                COALESCE(SUBSTRING(cpv_codes[1], 1, 2), 'NN') AS cpv_prefix,
                COUNT(*)                                        AS count
            FROM ted_notices
            WHERE notice_type = 'contract_notice'
              AND cpv_codes IS NOT NULL
              AND cpv_codes[1] IS NOT NULL
            GROUP BY cpv_prefix
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()

        # ── 4. GUS — produkcja budowlano-montażowa top-5 woj (od 2015) ──────
        gus_production = conn.execute(sa.text("""
            SELECT year, value, unit_name AS province
            FROM gus_indicators
            WHERE variable_name ILIKE '%produkcja%'
              AND unit_name IN ('MAZOWIECKIE','ŚLĄSKIE','MAŁOPOLSKIE','DOLNOŚLĄSKIE','WIELKOPOLSKIE')
              AND year >= 2015
            ORDER BY unit_name ASC, year ASC
        """)).fetchall()

        # ── 5. GUS — wynagrodzenia w budownictwie ────────────────────────────
        gus_wages = conn.execute(sa.text("""
            SELECT year, ROUND(AVG(value)::numeric, 2) AS avg_value
            FROM gus_indicators
            WHERE variable_name ILIKE '%wynagrodzen%'
            GROUP BY year
            ORDER BY year ASC
        """)).fetchall()

        # ── 6. BZP — top 10 CPV (8-znakowy prefix) ──────────────────────────
        bzp_cpv = conn.execute(sa.text("""
            SELECT
                SUBSTRING(cpv_main, 1, 8) AS cpv_code,
                COUNT(*)                   AS count
            FROM bzp_results
            WHERE cpv_main IS NOT NULL
            GROUP BY cpv_code
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()

        # ── 7. BZP — rozkład wg województwa (kody NUTS2/PL) ─────────────────
        # Normalizacja: kod PL02/PL04..  → mapujemy na pełną nazwę w frontendzie
        bzp_voivodeship = conn.execute(sa.text("""
            SELECT voivodeship AS province, COUNT(*) AS n
            FROM bzp_results
            WHERE voivodeship IS NOT NULL
              AND voivodeship != ''
            GROUP BY voivodeship
            ORDER BY n DESC
        """)).fetchall()

        # ── 8. Pre-tender — sygnały wg miesiąca ─────────────────────────────
        pretender_monthly = conn.execute(sa.text("""
            SELECT
                TO_CHAR(published_at, 'YYYY-MM') AS month,
                COUNT(*)                          AS count
            FROM pretender_signals
            WHERE published_at IS NOT NULL
            GROUP BY month
            ORDER BY month ASC
        """)).fetchall()

    return {
        "kpi": {
            "bzp_30d":             int(bzp_kpi.bzp_30d or 0),
            "unique_contractors":  int(bzp_kpi.unique_contractors or 0),
            "avg_value_k":         float(bzp_kpi.avg_value_k or 0),
            "total_value_bln":     float(bzp_kpi.total_value_bln or 0),
            "ted_30d":             int(ted_kpi.ted_30d or 0),
            "pretender_30d":       int(pretender_kpi.pretender_30d or 0),
            "gus_production_mln":  float(gus_latest.avg_production_mln or 0) if gus_latest else 0,
        },
        "bzp_weekly": [
            {"week": str(r.week), "count": r.count}
            for r in bzp_weekly
        ],
        "ted_types": [
            {"type": r.notice_type, "count": r.count}
            for r in ted_types
        ],
        "ted_cpv": [
            {"cpv": r.cpv_prefix, "count": r.count}
            for r in ted_cpv
        ],
        "gus_production": [
            {"period": str(r.year), "value": float(r.value or 0), "province": r.province}
            for r in gus_production
        ],
        "gus_wages": [
            {"period": str(r.year), "value": float(r.avg_value or 0)}
            for r in gus_wages
        ],
        "bzp_cpv": [
            {"cpv": r.cpv_code, "count": r.count}
            for r in bzp_cpv
        ],
        "bzp_voivodeship": [
            {"province": r.province, "n": r.n}
            for r in bzp_voivodeship
        ],
        "pretender_monthly": [
            {"month": r.month, "count": r.count}
            for r in pretender_monthly
        ],
    }
