"""Kosztorys v3 Router — FAZA 7.32: ICB/KNR real prices + AI wycena.

Endpoints:
  GET  /api/v2/icb/rates               — stawki ICB dla CPV5 + NUTS2
  POST /api/v2/kosztorys/{id}/ai-wycena-v2  — AI-wycena pozycji (SSE stream)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(tags=["kosztorys-v3"])
logger = logging.getLogger(__name__)

VLLM_BASE = "http://localhost:8001/v1"
VLLM_MODEL = "axon"
VLLM_KEY = "token-terra"


# ─── GET /api/v2/icb/rates ────────────────────────────────────────────────────

@router.get("/api/v2/icb/rates")
def get_icb_rates(
    user: AuthUser,
    cpv5: str,
    nuts2: str,
) -> dict:
    """Stawki ICB/KNR dla danego CPV5 i regionu NUTS2 (ostatnie 4 kwartały)."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT quarter, icb_r_rate, icb_m_rate, icb_s_rate,
                       avg_value, median_value, n_tenders
                FROM cpv_regional_benchmark
                WHERE cpv5 = :cpv5 AND nuts2_code = :nuts2
                ORDER BY quarter DESC
                LIMIT 4
            """),
            {"cpv5": cpv5, "nuts2": nuts2},
        ).fetchall()

    rates = []
    for r in rows:
        rates.append({
            "quarter": str(r.quarter),
            "r": float(r.icb_r_rate) if r.icb_r_rate is not None else None,
            "m": float(r.icb_m_rate) if r.icb_m_rate is not None else None,
            "s": float(r.icb_s_rate) if r.icb_s_rate is not None else None,
            "avg_val": float(r.avg_value) if r.avg_value is not None else None,
            "median_val": float(r.median_value) if r.median_value is not None else None,
            "n_tenders": r.n_tenders,
        })

    return {
        "cpv5": cpv5,
        "nuts2_code": nuts2,
        "rates": rates,
    }


# ─── POST /api/v2/kosztorys/{id}/ai-wycena-v2  (SSE) ─────────────────────────

@router.post("/api/v2/kosztorys/{kosztorys_id}/ai-wycena-v2")
async def ai_wycena_v2(kosztorys_id: str, user: AuthUser) -> StreamingResponse:
    """AI-wycena pozycji kosztorysu na podstawie stawek ICB. SSE stream."""
    engine = get_engine()

    # 1. Pobierz kosztorys + pozycje
    with engine.connect() as conn:
        krow = conn.execute(
            sa.text("""
                SELECT k.id, k.nazwa, k.tender_id, k.kwartalnr, k.kwartalrok
                FROM kosztorys k
                WHERE k.id = :kid
            """),
            {"kid": kosztorys_id},
        ).fetchone()
        if not krow:
            raise HTTPException(status_code=404, detail="Kosztorys nie znaleziony")

        pozycje = conn.execute(
            sa.text("""
                SELECT id, lp, opis, jednostka, ilosc, r_jcena, m_jcena, s_jcena,
                       kst_code, katalog
                FROM kosztorys_pozycja
                WHERE kosztorys_id = :kid
                ORDER BY lp
                LIMIT 50
            """),
            {"kid": kosztorys_id},
        ).fetchall()

        # 2. Pobierz ICB rates (użyj pierwszego CPV z tendera jeśli dostępny)
        icb_rates_txt = ""
        if krow.tender_id:
            tender_row = conn.execute(
                sa.text("SELECT cpv, nuts_code FROM tender WHERE id = :tid"),
                {"tid": str(krow.tender_id)},
            ).fetchone()
            if tender_row and tender_row.cpv:
                cpv_list = tender_row.cpv
                cpv5 = str(cpv_list[0])[:5] if cpv_list else None
                nuts2 = (tender_row.nuts_code or "")[:4] or None
                if cpv5 and nuts2:
                    icb_rows = conn.execute(
                        sa.text("""
                            SELECT quarter, icb_r_rate, icb_m_rate, icb_s_rate
                            FROM cpv_regional_benchmark
                            WHERE cpv5 = :cpv5 AND nuts2_code = :nuts2
                            ORDER BY quarter DESC LIMIT 2
                        """),
                        {"cpv5": cpv5, "nuts2": nuts2},
                    ).fetchall()
                    if icb_rows:
                        last = icb_rows[0]
                        icb_rates_txt = (
                            f"Stawki ICB (CPV5={cpv5}, NUTS2={nuts2}, kw={last.quarter}): "
                            f"R={last.icb_r_rate} zł/rbh, M={last.icb_m_rate} zł/jm, "
                            f"S={last.icb_s_rate} zł/jm"
                        )

    # 3. Zbuduj prompt
    pozycje_txt = "\n".join(
        f"  {p.lp}. {p.opis} [{p.jednostka}, ilość={float(p.ilosc):.2f}] "
        f"(r_jcena={float(p.r_jcena):.2f}, m_jcena={float(p.m_jcena):.2f}, s_jcena={float(p.s_jcena):.2f})"
        for p in pozycje
    )
    if not pozycje_txt:
        pozycje_txt = "  (brak pozycji w kosztorysie)"

    prompt = (
        f"Wycen następujące pozycje kosztorysu na podstawie stawek rynkowych.\n"
        f"Kosztorys: {krow.nazwa}\n"
        f"{icb_rates_txt}\n\n"
        f"Pozycje do wyceny:\n{pozycje_txt}\n\n"
        "Dla każdej pozycji podaj:\n"
        "- Sugerowaną stawkę robocizny (R) w zł/rbh\n"
        "- Sugerowaną stawkę materiałów (M) w zł/jm\n"
        "- Sugerowaną stawkę sprzętu (S) w zł/jm\n"
        "- Uzasadnienie w 1-2 zdaniach\n\n"
        "Format odpowiedzi: numerowana lista, jedna pozycja per linia.\n"
        "Podaj też podsumowanie łączne szacunkowej wartości kosztorysu."
    )

    async def _event_stream():
        payload = {
            "model": VLLM_MODEL,
            "messages": [
                {"role": "system", "content": "Jesteś ekspertem ds. kosztorysowania robót budowlanych (KNR/ICB)."},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "max_tokens": 2048,
            "temperature": 0.3,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{VLLM_BASE}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {VLLM_KEY}"},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield f"data: {json.dumps({'text': delta})}\n\n"
                            except Exception:
                                pass
        except Exception as exc:
            logger.warning("AI wycena stream error: %s", exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")
