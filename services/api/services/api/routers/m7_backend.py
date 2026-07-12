"""Settings + Reports + Market KPI + Bookmarks + Alerts + Webhooks + Team + Feedback + Axiom + BidIntelligence.

Phases 7.18-7.31 backend endpoints.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine
from services.ai.vllm_client import get_llm_client

router = APIRouter(prefix="/api/v2", tags=["m7-backend"])
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.18 — Settings
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/settings/usage")
def get_usage(tenant_id: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        tenders = conn.execute(sa.text(
            "SELECT COUNT(*) FROM tender WHERE tenant_id=:tid AND created_at >= date_trunc('month', now())"
        ), {"tid": tenant_id}).scalar()
        analyses = conn.execute(sa.text(
            "SELECT COUNT(*) FROM agent_run WHERE tenant_id=:tid AND started_at >= date_trunc('month', now())"
        ), {"tid": tenant_id}).scalar()
    return {"tenders_this_month": tenders or 0, "ai_analyses_this_month": analyses or 0}


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.19 — Reports
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reports/monthly")
def monthly_report(tenant_id: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status='decided_go') as won,
                COUNT(*) FILTER (WHERE status='decided_nogo') as lost,
                SUM(value_pln) FILTER (WHERE status != 'new') as pipeline_value,
                SUM(value_pln) FILTER (WHERE status='decided_go') as won_value
            FROM tender
            WHERE tenant_id=:tid AND created_at >= date_trunc('month', now())
        """), {"tid": tenant_id}).fetchone()
    return {
        "total": row[0], "won": row[1], "lost": row[2],
        "pipeline_value": float(row[3]) if row[3] else 0,
        "won_value": float(row[4]) if row[4] else 0,
        "win_rate_pct": round(row[1] * 100 / max(row[1] + row[2], 1), 1),
    }


@router.post("/reports/ai-summary")
def ai_summary(tenant_id: str) -> StreamingResponse:
    """AI-generated executive summary. SSE stream."""
    engine = get_engine()
    with engine.connect() as conn:
        stats = conn.execute(sa.text("""
            SELECT COUNT(*) as total,
                   COUNT(*) FILTER (WHERE status='decided_go') as won,
                   SUM(value_pln) FILTER (WHERE status='decided_go') as won_val,
                   COUNT(*) FILTER (WHERE deadline_at > NOW() AND deadline_at < NOW() + INTERVAL '7 days') as urgent
            FROM tender WHERE tenant_id=:tid
        """), {"tid": tenant_id}).fetchone()

    prompt = (
        f"Wygeneruj krótkie podsumowanie executive dla zarządu firmy budowlanej:\n"
        f"- Łącznie przetargów: {stats[0]}\n"
        f"- Wygranych: {stats[1]}\n"
        f"- Wartość wygranych: {stats[2] or 0} PLN\n"
        f"- Pilnych (deadline <7 dni): {stats[3]}\n"
        f"Napisz 3-4 zdania z rekomendacją działania."
    )

    llm = get_llm_client()

    def stream():
        for token in llm.generate_stream(prompt):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/reports/templates")
def report_templates() -> list[dict]:
    return [
        {"id": "zarzad", "name": "Zarząd", "description": "Executive summary — KPI, win rate, pipeline value"},
        {"id": "handlowiec", "name": "Handlowiec", "description": "Hot tenders, deadlines, follow-ups"},
        {"id": "techniczny", "name": "Techniczny", "description": "Kosztorysy, materiały, zasoby"},
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.20 — Market KPI Bar
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/market/kpi-bar")
def market_kpi_bar() -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT
                COUNT(*) FILTER (WHERE created_at >= date_trunc('day', now())) as new_today,
                COALESCE(SUM(value_pln) FILTER (WHERE created_at >= date_trunc('day', now())), 0) as value_today,
                COUNT(*) as total_all
            FROM tender
        """)).fetchone()
    return {
        "new_today": row[0] or 0,
        "value_today": float(row[1]) if row[1] else 0,
        "total_tenders": row[2] or 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.21 — Bookmarks + Alerts
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/bookmarks")
def get_bookmarks(tenant_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT tb.id, tb.tender_id, t.title, t.value_pln, t.deadline_at, tb.priority, tb.notes, tb.created_at
            FROM tender_bookmark tb
            JOIN tender t ON t.id = tb.tender_id
            WHERE tb.tenant_id = :tid
            ORDER BY tb.priority DESC, tb.created_at DESC
        """), {"tid": tenant_id}).fetchall()
    return [
        {"id": str(r[0]), "tender_id": str(r[1]), "title": r[2],
         "value_pln": float(r[3]) if r[3] else None,
         "deadline_at": str(r[4]) if r[4] else None,
         "priority": r[5], "notes": r[6], "created_at": str(r[7])}
        for r in rows
    ]


class BookmarkRequest(BaseModel):
    priority: int = 0
    notes: str = ""


@router.post("/bookmarks/{tender_id}")
def add_bookmark(tender_id: str, tenant_id: str, body: BookmarkRequest | None = None) -> dict:
    engine = get_engine()
    bm_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO tender_bookmark (id, tenant_id, tender_id, priority, notes)
            VALUES (:id, :tid, :tender, :pri, :notes)
            ON CONFLICT (tenant_id, tender_id) DO UPDATE SET priority=:pri, notes=:notes
        """), {"id": bm_id, "tid": tenant_id, "tender": tender_id,
               "pri": body.priority if body else 0, "notes": body.notes if body else ""})
    return {"id": bm_id, "status": "bookmarked"}


@router.delete("/bookmarks/{tender_id}")
def remove_bookmark(tender_id: str, tenant_id: str) -> dict:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text(
            "DELETE FROM tender_bookmark WHERE tenant_id=:tid AND tender_id=:tender"
        ), {"tid": tenant_id, "tender": tender_id})
    return {"status": "removed"}


# Alerts
@router.get("/alerts")
def get_alerts(tenant_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, name, cpv_prefixes, keywords, min_value, max_value, active, created_at
            FROM tender_alert WHERE tenant_id=:tid ORDER BY created_at DESC
        """), {"tid": tenant_id}).fetchall()
    return [
        {"id": str(r[0]), "name": r[1], "cpv_prefixes": r[2], "keywords": r[3],
         "min_value": float(r[4]) if r[4] else None,
         "max_value": float(r[5]) if r[5] else None,
         "active": r[6], "created_at": str(r[7])}
        for r in rows
    ]


class AlertRequest(BaseModel):
    name: str
    cpv_prefixes: list[str] = []
    keywords: list[str] = []
    min_value: float | None = None
    max_value: float | None = None


@router.post("/alerts")
def create_alert(tenant_id: str, body: AlertRequest) -> dict:
    engine = get_engine()
    alert_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO tender_alert (id, tenant_id, name, cpv_prefixes, keywords, min_value, max_value)
            VALUES (:id, :tid, :name, :cpv, :kw, :min, :max)
        """), {"id": alert_id, "tid": tenant_id, "name": body.name,
               "cpv": body.cpv_prefixes, "kw": body.keywords,
               "min": body.min_value, "max": body.max_value})
    return {"id": alert_id, "status": "created"}


@router.post("/alerts/{alert_id}/test")
def test_alert(alert_id: str, tenant_id: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        alert = conn.execute(sa.text(
            "SELECT cpv_prefixes, keywords, min_value, max_value FROM tender_alert WHERE id=:id"
        ), {"id": alert_id}).fetchone()
    if not alert:
        return {"error": "alert not found"}

    # Simple match count
    sql = "SELECT COUNT(*) FROM tender WHERE tenant_id=:tid"
    params: dict = {"tid": tenant_id}
    if alert[2]:  # min_value
        sql += " AND value_pln >= :min"
        params["min"] = float(alert[2])
    if alert[3]:  # max_value
        sql += " AND value_pln <= :max"
        params["max"] = float(alert[3])

    with engine.connect() as conn:
        count = conn.execute(sa.text(sql), params).scalar()
    return {"matching_tenders": count or 0}


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.22 — Automation Webhooks
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/webhooks")
def list_webhooks(tenant_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, name, url, events, active, created_at
            FROM automation_webhook WHERE tenant_id=:tid ORDER BY created_at DESC
        """), {"tid": tenant_id}).fetchall()
    return [
        {"id": str(r[0]), "name": r[1], "url": r[2], "events": r[3], "active": r[4], "created_at": str(r[5])}
        for r in rows
    ]


class WebhookRequest(BaseModel):
    name: str
    url: str
    events: list[str] = ["tender.new", "tender.scored"]
    secret: str = ""


@router.post("/webhooks")
def create_webhook(tenant_id: str, body: WebhookRequest) -> dict:
    engine = get_engine()
    wh_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO automation_webhook (id, tenant_id, name, url, events, secret)
            VALUES (:id, :tid, :name, :url, :events, :secret)
        """), {"id": wh_id, "tid": tenant_id, "name": body.name,
               "url": body.url, "events": body.events, "secret": body.secret})
    return {"id": wh_id, "status": "created"}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: str) -> dict:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("DELETE FROM automation_webhook WHERE id=:id"), {"id": webhook_id})
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.23 — Team
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/team/members")
def team_members(tenant_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT u.id, u.email, u.full_name, uo.role, u.created_at
            FROM "user" u
            JOIN user_org uo ON uo.user_id = u.id
            WHERE uo.org_id = :tid
            ORDER BY u.created_at
        """), {"tid": tenant_id}).fetchall()
    return [
        {"id": str(r[0]), "email": r[1], "full_name": r[2], "role": r[3], "created_at": str(r[4])}
        for r in rows
    ]


@router.get("/team/activity")
def team_activity(tenant_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT al.user_id, u.email,
                   COUNT(*) FILTER (WHERE al.action='analyze') as analyses,
                   COUNT(*) FILTER (WHERE al.action='decision') as decisions,
                   COUNT(*) as total_actions
            FROM audit_log al
            JOIN "user" u ON u.id = al.user_id
            WHERE al.tenant_id=:tid AND al.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY al.user_id, u.email
        """), {"tid": tenant_id}).fetchall()
    return [
        {"user_id": str(r[0]), "email": r[1], "analyses": r[2], "decisions": r[3], "total": r[4]}
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.28 — Feedback
# ═══════════════════════════════════════════════════════════════════════════════

class FeedbackRequest(BaseModel):
    agent_run_id: str | None = None
    tender_id: str | None = None
    rating: int
    comment: str = ""


@router.post("/feedback")
def submit_feedback(tenant_id: str, body: FeedbackRequest) -> dict:
    engine = get_engine()
    fb_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO ai_feedback (id, tenant_id, agent_run_id, tender_id, rating, comment)
            VALUES (:id, :tid, :arid, :tender, :rating, :comment)
        """), {"id": fb_id, "tid": tenant_id, "arid": body.agent_run_id,
               "tender": body.tender_id, "rating": body.rating, "comment": body.comment})
    return {"id": fb_id, "status": "saved"}


@router.get("/feedback/stats")
def feedback_stats(tenant_id: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT COUNT(*), AVG(rating), COUNT(*) FILTER (WHERE rating >= 4)
            FROM ai_feedback WHERE tenant_id=:tid
        """), {"tid": tenant_id}).fetchone()
    return {
        "total": row[0] or 0,
        "avg_rating": round(float(row[1]), 2) if row[1] else 0,
        "positive_count": row[2] or 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.30 — Axiom Engine
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/axioms")
def list_axioms(tenant_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, class, code, body, description, active
            FROM axiom WHERE tenant_id=:tid AND active=true ORDER BY code
        """), {"tid": tenant_id}).fetchall()
    return [
        {"id": str(r[0]), "class": r[1], "code": r[2], "body": r[3], "description": r[4], "active": r[5]}
        for r in rows
    ]


class AxiomRequest(BaseModel):
    axiom_class: str = "BLOCK"
    code: str
    body: str
    description: str = ""


@router.post("/axioms")
def create_axiom(tenant_id: str, body: AxiomRequest) -> dict:
    engine = get_engine()
    ax_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO axiom (id, tenant_id, class, code, body, description)
            VALUES (:id, :tid, :cls, :code, :body, :desc)
        """), {"id": ax_id, "tid": tenant_id, "cls": body.axiom_class,
               "code": body.code, "body": body.body, "desc": body.description})
    return {"id": ax_id, "status": "created"}


@router.post("/axioms/evaluate/{tender_id}")
def evaluate_axioms(tender_id: str, tenant_id: str) -> list[dict]:
    """Evaluate all active axioms against a tender."""
    engine = get_engine()
    with engine.connect() as conn:
        tender = conn.execute(sa.text(
            "SELECT title, value_pln, cpv, voivodeship, deadline_at FROM tender WHERE id=:id"
        ), {"id": tender_id}).fetchone()
        axioms = conn.execute(sa.text(
            "SELECT id, class, code, body FROM axiom WHERE tenant_id=:tid AND active=true"
        ), {"tid": tenant_id}).fetchall()

    if not tender:
        return [{"error": "tender not found"}]

    results = []
    tender_ctx = {
        "title": tender[0], "value_pln": float(tender[1]) if tender[1] else 0,
        "cpv": tender[2], "voivodeship": tender[3],
        "deadline_at": str(tender[4]) if tender[4] else None,
    }

    for ax in axioms:
        try:
            # Safe eval of rule body against tender data
            matched = eval(ax[3], {"__builtins__": {}}, {"tender": tender_ctx})
            results.append({
                "axiom_id": str(ax[0]), "class": ax[1], "code": ax[2],
                "matched": bool(matched), "reason": f"Rule {ax[2]} {'MATCHED' if matched else 'not matched'}",
            })
        except Exception as e:
            results.append({
                "axiom_id": str(ax[0]), "class": ax[1], "code": ax[2],
                "matched": False, "reason": f"Eval error: {e}",
            })

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 7.31 — BidIntelligence
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/bid-intelligence")
def get_bid_intelligence(tenant_id: str, limit: int = 50) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT bi.id, bi.tender_id, t.title, bi.our_price, bi.winning_price,
                   bi.rank_position, bi.won, bi.markup_pct, bi.bid_date
            FROM bid_intelligence bi
            JOIN tender t ON t.id = bi.tender_id
            WHERE bi.tenant_id=:tid
            ORDER BY bi.bid_date DESC LIMIT :lim
        """), {"tid": tenant_id, "lim": limit}).fetchall()
    return [
        {"id": str(r[0]), "tender_id": str(r[1]), "title": r[2],
         "our_price": float(r[3]) if r[3] else None,
         "winning_price": float(r[4]) if r[4] else None,
         "rank_position": r[5], "won": r[6],
         "markup_pct": float(r[7]) if r[7] else None,
         "bid_date": str(r[8]) if r[8] else None}
        for r in rows
    ]


class BidIntelRequest(BaseModel):
    tender_id: str
    our_price: float
    winning_price: float | None = None
    rank_position: int | None = None
    won: bool = False
    markup_pct: float | None = None


@router.post("/bid-intelligence")
def add_bid_intel(tenant_id: str, body: BidIntelRequest) -> dict:
    engine = get_engine()
    bi_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO bid_intelligence (id, tenant_id, tender_id, our_price, winning_price, rank_position, won, markup_pct, bid_date)
            VALUES (:id, :tid, :tender, :our, :win, :rank, :won, :markup, NOW())
        """), {"id": bi_id, "tid": tenant_id, "tender": body.tender_id,
               "our": body.our_price, "win": body.winning_price,
               "rank": body.rank_position, "won": body.won, "markup": body.markup_pct})
    return {"id": bi_id, "status": "recorded"}


@router.get("/bid-intelligence/optimal-markup")
def optimal_markup(tenant_id: str, cpv5: str | None = None) -> dict:
    engine = get_engine()
    sql = """
        SELECT
            COUNT(*) as total,
            AVG(markup_pct) FILTER (WHERE won=true) as avg_winning_markup,
            AVG(markup_pct) FILTER (WHERE won=false) as avg_losing_markup,
            COUNT(*) FILTER (WHERE won=true) as wins,
            ROUND(COUNT(*) FILTER (WHERE won=true) * 100.0 / NULLIF(COUNT(*), 0), 1) as win_rate
        FROM bid_intelligence bi
        JOIN tender t ON t.id = bi.tender_id
        WHERE bi.tenant_id=:tid
    """
    params: dict = {"tid": tenant_id}
    if cpv5:
        sql += " AND EXISTS (SELECT 1 FROM UNNEST(t.cpv) c WHERE LEFT(c,5) = :cpv5)"
        params["cpv5"] = cpv5

    with engine.connect() as conn:
        row = conn.execute(sa.text(sql), params).fetchone()

    if not row or not row[0]:
        return {"sample_size": 0, "recommendation": "Za mało danych"}

    avg_win = float(row[1]) if row[1] else 0
    avg_lose = float(row[2]) if row[2] else 0
    recommended = round((avg_win * 0.7 + avg_lose * 0.3), 1) if avg_win else avg_lose * 0.8

    return {
        "sample_size": row[0],
        "avg_winning_markup_pct": round(avg_win, 1),
        "avg_losing_markup_pct": round(avg_lose, 1),
        "recommended_markup_pct": recommended,
        "win_rate_pct": float(row[4]) if row[4] else 0,
        "cpv5": cpv5,
    }


@router.get("/bid-intelligence/stats")
def bid_intel_stats(tenant_id: str) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT COUNT(*), AVG(markup_pct), AVG(rank_position),
                   COUNT(*) FILTER (WHERE won=true),
                   ROUND(COUNT(*) FILTER (WHERE won=true) * 100.0 / NULLIF(COUNT(*),0), 1)
            FROM bid_intelligence WHERE tenant_id=:tid
        """), {"tid": tenant_id}).fetchone()
    return {
        "total_bids": row[0] or 0,
        "avg_markup_pct": round(float(row[1]), 1) if row[1] else 0,
        "avg_rank": round(float(row[2]), 1) if row[2] else 0,
        "total_wins": row[3] or 0,
        "win_rate_pct": float(row[4]) if row[4] else 0,
    }
