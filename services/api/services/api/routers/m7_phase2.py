"""M7 Phase 7.12-7.17 — BuyerCRM, Competitor Watch, MarketIntel, Notifications, Command Menu.

Endpoints:
  # BuyerCRM
  GET    /api/v2/buyers                  — lista zamawiających z metrykami
  GET    /api/v2/buyers/{id}             — szczegóły zamawiającego
  GET    /api/v2/buyers/{id}/history     — historia przetargów danego zamawiającego
  GET    /api/v2/buyers/{id}/insights    — AI insights (patterns, seasonality, avg values)

  # Competitor Watch
  GET    /api/v2/competitors             — lista śledzonych konkurentów
  GET    /api/v2/competitors/{id}/wins   — wygrane przetargi konkurenta
  GET    /api/v2/competitors/heatmap     — heatmap CPV × competitor (kto gdzie wygrywa)

  # MarketIntel
  GET    /api/v2/market-intel/overview   — syntetyczny obraz rynku
  GET    /api/v2/market-intel/cpv-trends — trendy CPV (volume, value, growth)
  GET    /api/v2/market-intel/regional   — analiza regionalna

  # Notifications
  GET    /api/v2/notifications           — powiadomienia użytkownika
  PATCH  /api/v2/notifications/{id}/read — oznacz jako przeczytane
  GET    /api/v2/notifications/unread-count

  # Command Menu
  GET    /api/v2/command/search?q=...    — unified search (tenders+buyers+competitors+materials)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(tags=["m7-phase-12-17"])
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# BUYER CRM
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/v2/buyers")
def list_buyers(
    q: str | None = None,
    sort: str = "tender_count",
    limit: int = 50,
) -> dict:
    """Lista zamawiających z metrykami (tender_count, total_value, avg_value, last_seen)."""
    engine = get_engine()
    search_filter = ""
    params: dict = {"limit": limit}
    if q:
        search_filter = "WHERE buyer ILIKE :q"
        params["q"] = f"%{q}%"

    order_map = {
        "tender_count": "tender_count DESC",
        "total_value": "total_value DESC",
        "last_seen": "last_seen DESC",
        "name": "buyer ASC",
    }
    order = order_map.get(sort, "tender_count DESC")

    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT buyer,
                   COUNT(*) as tender_count,
                   COALESCE(SUM(value_pln), 0) as total_value,
                   ROUND(AVG(value_pln)::numeric, 0) as avg_value,
                   MAX(published_at) as last_seen,
                   array_agg(DISTINCT COALESCE((cpv::jsonb->>0)::text, '')) as cpvs
            FROM tender
            WHERE buyer IS NOT NULL AND buyer != ''
            {search_filter.replace('WHERE', 'AND') if search_filter else ''}
            GROUP BY buyer
            ORDER BY {order}
            LIMIT :limit
        """), params).fetchall()

    return {
        "count": len(rows),
        "buyers": [
            {
                "name": r[0],
                "tender_count": r[1],
                "total_value": float(r[2]),
                "avg_value": float(r[3]) if r[3] else 0,
                "last_seen": str(r[4]) if r[4] else None,
                "top_cpvs": [c for c in (r[5] or []) if c][:5],
            }
            for r in rows
        ],
    }


@router.get("/api/v2/buyers/{buyer_name}/history")
def buyer_history(buyer_name: str, limit: int = 20) -> dict:
    """Historia przetargów zamawiającego."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, title, value_pln, status, published_at, deadline_at, cpv, match_score
            FROM tender
            WHERE buyer = :name
            ORDER BY published_at DESC
            LIMIT :limit
        """), {"name": buyer_name, "limit": limit}).fetchall()

    return {
        "buyer": buyer_name,
        "tender_count": len(rows),
        "history": [
            {
                "id": str(r[0]), "title": r[1], "value_pln": float(r[2]) if r[2] else 0,
                "status": r[3], "published_at": str(r[4]) if r[4] else None,
                "deadline_at": str(r[5]) if r[5] else None,
                "cpv": r[6], "match_score": float(r[7]) if r[7] else None,
            }
            for r in rows
        ],
    }


@router.get("/api/v2/buyers/{buyer_name}/insights")
def buyer_insights(buyer_name: str) -> dict:
    """AI insights — wzorce zamawiającego (sezonowość, wartości, CPV)."""
    engine = get_engine()
    with engine.connect() as conn:
        # Stats
        stats = conn.execute(sa.text("""
            SELECT COUNT(*) as cnt,
                   ROUND(AVG(value_pln)::numeric, 0) as avg_val,
                   ROUND(MIN(value_pln)::numeric, 0) as min_val,
                   ROUND(MAX(value_pln)::numeric, 0) as max_val,
                   MIN(published_at) as first_seen,
                   MAX(published_at) as last_seen
            FROM tender WHERE buyer = :name
        """), {"name": buyer_name}).fetchone()

        # Seasonality — which months they publish most
        months = conn.execute(sa.text("""
            SELECT EXTRACT(MONTH FROM published_at)::int as m, COUNT(*) as cnt
            FROM tender WHERE buyer = :name AND published_at IS NOT NULL
            GROUP BY m ORDER BY cnt DESC
        """), {"name": buyer_name}).fetchall()

        # CPV distribution
        cpvs = conn.execute(sa.text("""
            SELECT cpv, COUNT(*) as cnt, ROUND(AVG(value_pln)::numeric, 0) as avg_val
            FROM tender WHERE buyer = :name AND cpv IS NOT NULL
            GROUP BY cpv ORDER BY cnt DESC LIMIT 5
        """), {"name": buyer_name}).fetchall()

    # Determine seasonality
    peak_months = [int(r[0]) for r in months[:3]] if months else []
    month_names = {1: "sty", 2: "lut", 3: "mar", 4: "kwi", 5: "maj", 6: "cze",
                   7: "lip", 8: "sie", 9: "wrz", 10: "paź", 11: "lis", 12: "gru"}

    return {
        "buyer": buyer_name,
        "total_tenders": stats[0] if stats else 0,
        "avg_value": float(stats[1]) if stats and stats[1] else 0,
        "min_value": float(stats[2]) if stats and stats[2] else 0,
        "max_value": float(stats[3]) if stats and stats[3] else 0,
        "active_since": str(stats[4]) if stats and stats[4] else None,
        "last_active": str(stats[5]) if stats and stats[5] else None,
        "seasonality": {
            "peak_months": [month_names.get(m, str(m)) for m in peak_months],
            "monthly_distribution": [{"month": int(r[0]), "count": r[1]} for r in months],
        },
        "cpv_focus": [
            {"cpv": str(r[0]), "count": r[1], "avg_value": float(r[2]) if r[2] else 0}
            for r in cpvs
        ],
        "recommendation": f"Zamawiający aktywny głównie w {', '.join(month_names.get(m, '') for m in peak_months)}. "
                          f"Średnia wartość: {float(stats[1] or 0):,.0f} PLN."
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITOR WATCH
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/v2/competitors")
def list_competitors(limit: int = 30) -> dict:
    """Lista konkurentów (z atlas_contractors) + ich metryki."""
    engine = get_engine()
    with engine.connect() as conn:
        # Try atlas_contractors first
        try:
            rows = conn.execute(sa.text("""
                SELECT name, city, nip, win_count, bid_count,
                       ROUND(win_count::numeric / NULLIF(bid_count, 0), 4) as win_rate,
                       total_won_value
                FROM atlas_contractors
                ORDER BY win_count DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()

            return {
                "count": len(rows),
                "competitors": [
                    {
                        "name": r[0], "city": r[1], "nip": r[2],
                        "win_count": r[3], "bid_count": r[4],
                        "win_rate": float(r[5]) if r[5] else 0,
                        "total_won_value": float(r[6]) if r[6] else 0,
                    }
                    for r in rows
                ],
            }
        except Exception:
            return {"count": 0, "competitors": [], "note": "atlas_contractors not available"}


@router.get("/api/v2/competitors/heatmap")
def competitor_heatmap() -> dict:
    """Heatmap: które firmy wygrywają w których CPV."""
    engine = get_engine()
    with engine.connect() as conn:
        try:
            rows = conn.execute(sa.text("""
                SELECT ac.name, t.cpv, COUNT(*) as wins, ROUND(SUM(t.value_pln)::numeric, 0) as total_value
                FROM atlas_contractors ac
                JOIN tender t ON t.winner_name = ac.name
                WHERE t.status = 'won' AND t.cpv IS NOT NULL
                GROUP BY ac.name, t.cpv
                ORDER BY wins DESC
                LIMIT 100
            """)).fetchall()

            return {
                "heatmap": [
                    {"competitor": r[0], "cpv": str(r[1]), "wins": r[2], "total_value": float(r[3]) if r[3] else 0}
                    for r in rows
                ]
            }
        except Exception as e:
            return {"heatmap": [], "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/v2/market-intel/overview")
def market_overview() -> dict:
    """Syntetyczny obraz rynku przetargowego."""
    engine = get_engine()
    with engine.connect() as conn:
        # Total stats
        total = conn.execute(sa.text("""
            SELECT COUNT(*) as cnt,
                   COALESCE(SUM(value_pln), 0) as total_val,
                   COUNT(DISTINCT buyer) as buyers,
                   COUNT(*) FILTER (WHERE published_at >= NOW() - INTERVAL '30 days') as last_30d,
                   COALESCE(SUM(value_pln) FILTER (WHERE published_at >= NOW() - INTERVAL '30 days'), 0) as val_30d
            FROM tender
        """)).fetchone()

        # Top CPVs
        cpvs = conn.execute(sa.text("""
            SELECT cpv, COUNT(*) as cnt, ROUND(SUM(value_pln)::numeric, 0) as total_val
            FROM tender WHERE cpv IS NOT NULL
            GROUP BY cpv ORDER BY cnt DESC LIMIT 10
        """)).fetchall()

        # Monthly volume trend (last 12 months)
        monthly = conn.execute(sa.text("""
            SELECT DATE_TRUNC('month', published_at)::date as month,
                   COUNT(*) as cnt,
                   ROUND(SUM(value_pln)::numeric, 0) as val
            FROM tender
            WHERE published_at >= NOW() - INTERVAL '12 months'
            GROUP BY month ORDER BY month
        """)).fetchall()

    return {
        "total_tenders": total[0],
        "total_value_pln": float(total[1]),
        "unique_buyers": total[2],
        "last_30d_count": total[3],
        "last_30d_value": float(total[4]),
        "top_cpvs": [{"cpv": str(r[0]), "count": r[1], "value": float(r[2]) if r[2] else 0} for r in cpvs],
        "monthly_trend": [
            {"month": str(r[0]), "count": r[1], "value": float(r[2]) if r[2] else 0}
            for r in monthly
        ],
    }


@router.get("/api/v2/market-intel/cpv-trends")
def cpv_trends(limit: int = 15) -> list[dict]:
    """Trendy CPV — volume, value, growth YoY."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            WITH current_year AS (
                SELECT cpv, COUNT(*) as cnt, COALESCE(SUM(value_pln), 0) as val
                FROM tender WHERE published_at >= DATE_TRUNC('year', NOW())
                GROUP BY cpv
            ), prev_year AS (
                SELECT cpv, COUNT(*) as cnt, COALESCE(SUM(value_pln), 0) as val
                FROM tender
                WHERE published_at >= DATE_TRUNC('year', NOW()) - INTERVAL '1 year'
                  AND published_at < DATE_TRUNC('year', NOW())
                GROUP BY cpv
            )
            SELECT c.cpv, c.cnt, c.val,
                   ROUND(((c.cnt - COALESCE(p.cnt, 0))::numeric / NULLIF(p.cnt, 0) * 100), 1) as growth_pct
            FROM current_year c
            LEFT JOIN prev_year p ON p.cpv = c.cpv
            ORDER BY c.val DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()

    return [
        {
            "cpv": str(r[0]), "count_this_year": r[1],
            "value_this_year": float(r[2]),
            "yoy_growth_pct": float(r[3]) if r[3] else None,
        }
        for r in rows
    ]


@router.get("/api/v2/market-intel/regional")
def market_regional() -> list[dict]:
    """Analiza regionalna rynku przetargowego."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT region, COUNT(*) as cnt,
                   ROUND(SUM(value_pln)::numeric, 0) as total_val,
                   ROUND(AVG(value_pln)::numeric, 0) as avg_val
            FROM tender
            WHERE region IS NOT NULL AND region != ''
            GROUP BY region
            ORDER BY total_val DESC
        """)).fetchall()

    return [
        {"region": r[0], "tender_count": r[1], "total_value": float(r[2]) if r[2] else 0, "avg_value": float(r[3]) if r[3] else 0}
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/v2/notifications")
def list_notifications(limit: int = 30, unread_only: bool = False) -> dict:
    """Powiadomienia użytkownika."""
    engine = get_engine()
    filter_clause = "WHERE is_read = false" if unread_only else ""
    with engine.connect() as conn:
        try:
            rows = conn.execute(sa.text(f"""
                SELECT id, type, title, body, is_read, created_at, metadata
                FROM notifications
                {filter_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()

            return {
                "count": len(rows),
                "notifications": [
                    {
                        "id": str(r[0]), "type": r[1], "title": r[2], "body": r[3],
                        "is_read": r[4], "created_at": str(r[5]),
                        "metadata": r[6],
                    }
                    for r in rows
                ],
            }
        except Exception:
            return {"count": 0, "notifications": [], "note": "notifications table not yet created"}


@router.get("/api/v2/notifications/unread-count")
def unread_count() -> dict:
    """Licznik nieprzeczytanych powiadomień."""
    engine = get_engine()
    with engine.connect() as conn:
        try:
            cnt = conn.execute(sa.text(
                "SELECT COUNT(*) FROM notifications WHERE is_read = false"
            )).scalar()
            return {"unread": cnt}
        except Exception:
            return {"unread": 0}


@router.patch("/api/v2/notifications/{notification_id}/read")
def mark_read(notification_id: str) -> dict:
    """Oznacz powiadomienie jako przeczytane."""
    engine = get_engine()
    with engine.begin() as conn:
        try:
            conn.execute(sa.text(
                "UPDATE notifications SET is_read = true WHERE id = :id"
            ), {"id": notification_id})
            return {"ok": True}
        except Exception:
            return {"ok": False}


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND MENU — unified search
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/v2/command/search")
def command_search(q: str = Query(..., min_length=2)) -> dict:
    """Unified search across tenders, buyers, materials — for command palette (⌘K)."""
    engine = get_engine()
    results: list[dict] = []

    with engine.connect() as conn:
        # Search tenders
        tenders = conn.execute(sa.text("""
            SELECT id, title, buyer, value_pln, status
            FROM tender
            WHERE title ILIKE :q OR buyer ILIKE :q
            ORDER BY published_at DESC LIMIT 5
        """), {"q": f"%{q}%"}).fetchall()
        for r in tenders:
            results.append({
                "type": "tender", "id": str(r[0]),
                "title": r[1], "subtitle": f"{r[2]} • {r[3]:,.0f} PLN" if r[3] else r[2],
                "status": r[4], "url": f"/pipeline?id={r[0]}",
            })

        # Search buyers
        buyers = conn.execute(sa.text("""
            SELECT buyer, COUNT(*) as cnt
            FROM tender WHERE buyer ILIKE :q AND buyer IS NOT NULL
            GROUP BY buyer ORDER BY cnt DESC LIMIT 3
        """), {"q": f"%{q}%"}).fetchall()
        for r in buyers:
            results.append({
                "type": "buyer",
                "title": r[0], "subtitle": f"{r[1]} przetargów",
                "url": f"/buyers?name={r[0]}",
            })

        # Search ICB materials
        materials = conn.execute(sa.text("""
            SELECT nazwa, symbol, cena_netto, jednostka, category
            FROM icb_ceny_srednie
            WHERE (nazwa ILIKE :q OR symbol ILIKE :q)
              AND kwartalrok = (SELECT MAX(kwartalrok) FROM icb_ceny_srednie)
            ORDER BY cena_netto DESC LIMIT 3
        """), {"q": f"%{q}%"}).fetchall()
        for r in materials:
            results.append({
                "type": "material",
                "title": r[0], "subtitle": f"{float(r[2]):.2f} PLN/{r[3]} ({r[4]})",
                "symbol": r[1], "url": f"/icb?q={r[0]}",
            })

    return {"query": q, "count": len(results), "results": results}
