"""S4 — External Data Intelligence router.

Źródła:
- TED Notices (Tenders Electronic Daily — UE)
- GUS BDL (Bank Danych Lokalnych — wskaźniki budownictwa)
- Pre-tender Signals (sygnały przed-przetargowe)
- AI Market Intelligence (Qwen/Bedrock summary)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/external", tags=["external-data"])


# ─── TED Notices ─────────────────────────────────────────────────────────────

@router.get("/ted")
async def get_ted_notices(
    user: AuthUser,
    cpv_prefix: Optional[str] = Query(None, description="Prefix CPV, np. '45'"),
    days_back: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Ogłoszenia przetargowe TED (UE) dla Polski z filtrem CPV."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Sprawdź czy tabela istnieje
            exists = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='ted_notices')"
            )).scalar()
            if not exists:
                return {"items": [], "total": 0, "message": "Tabela ted_notices jeszcze nie istnieje — uruchom import."}

            cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
            base_where = "WHERE publication_date >= :cutoff"
            params: dict = {"cutoff": cutoff.date(), "limit": limit, "offset": offset}

            if cpv_prefix:
                base_where += " AND EXISTS(SELECT 1 FROM unnest(cpv_codes) c WHERE c LIKE :cpv_pat)"
                params["cpv_pat"] = f"{cpv_prefix}%"

            rows = conn.execute(text(f"""
                SELECT ted_id, title, buyer, cpv_codes,
                       contract_value_eur, contract_value_pln,
                       publication_date, notice_type
                FROM ted_notices
                {base_where}
                ORDER BY publication_date DESC
                LIMIT :limit OFFSET :offset
            """), params).fetchall()

            total = conn.execute(text(f"""
                SELECT COUNT(*) FROM ted_notices {base_where}
            """), {k: v for k, v in params.items() if k not in ("limit", "offset")}).scalar()

            return {
                "items": [dict(r._mapping) for r in rows],
                "total": total,
                "days_back": days_back,
                "cpv_prefix": cpv_prefix,
            }
    except Exception as e:
        logger.error("TED endpoint error: %s", e)
        return {"items": [], "total": 0, "error": str(e)}


# ─── GUS Indicators ──────────────────────────────────────────────────────────

@router.get("/gus/indicators")
async def get_gus_indicators(
    user: AuthUser,
    year: Optional[int] = Query(None, description="Rok danych, np. 2024"),
):
    """Wskaźniki GUS BDL dla budownictwa (produkcja, liczba budów, wynagrodzenia)."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='gus_indicators')"
            )).scalar()
            if not exists:
                return {"items": [], "message": "Tabela gus_indicators jeszcze nie istnieje."}

            params: dict = {}
            where = ""
            if year:
                where = "WHERE year = :year"
                params["year"] = year

            rows = conn.execute(text(f"""
                SELECT variable_id, variable_name, unit_name, year, value
                FROM gus_indicators
                {where}
                ORDER BY variable_name, year DESC, value DESC NULLS LAST
            """), params).fetchall()

            # Grupuj po zmiennej
            grouped: dict = {}
            for r in rows:
                vname = r.variable_name or r.variable_id
                if vname not in grouped:
                    grouped[vname] = []
                grouped[vname].append({
                    "unit": r.unit_name,
                    "year": r.year,
                    "value": float(r.value) if r.value is not None else None,
                })

            return {"indicators": grouped, "total_records": len(rows)}
    except Exception as e:
        logger.error("GUS endpoint error: %s", e)
        return {"indicators": {}, "error": str(e)}


# ─── Pre-tender Signals ───────────────────────────────────────────────────────

@router.get("/pretenders")
async def get_pretender_signals(
    user: AuthUser,
    cpv_prefix: Optional[str] = Query(None),
    source: Optional[str] = Query(None, description="np. bzp_pin, ezamowienia_plan"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Sygnały pre-przetargowe (PIN, plany zamówień) — informacje przed formalnym przetargiem."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='pretender_signals')"
            )).scalar()
            if not exists:
                return {"items": [], "total": 0, "message": "Tabela pretender_signals jeszcze nie istnieje."}

            conditions = []
            params: dict = {"limit": limit, "offset": offset}

            if cpv_prefix:
                conditions.append("EXISTS(SELECT 1 FROM unnest(cpv_codes) c WHERE c LIKE :cpv_pat)")
                params["cpv_pat"] = f"{cpv_prefix}%"
            if source:
                conditions.append("source = :source")
                params["source"] = source

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

            rows = conn.execute(text(f"""
                SELECT signal_id, source, title, buyer,
                       estimated_value_pln, cpv_codes,
                       expected_date, published_at
                FROM pretender_signals
                {where}
                ORDER BY COALESCE(expected_date, published_at::date) ASC NULLS LAST
                LIMIT :limit OFFSET :offset
            """), params).fetchall()

            total = conn.execute(text(f"""
                SELECT COUNT(*) FROM pretender_signals {where}
            """), {k: v for k, v in params.items() if k not in ("limit", "offset")}).scalar()

            return {
                "items": [dict(r._mapping) for r in rows],
                "total": total,
            }
    except Exception as e:
        logger.error("Pre-tender endpoint error: %s", e)
        return {"items": [], "total": 0, "error": str(e)}


# ─── AI Market Intelligence ───────────────────────────────────────────────────

@router.get("/market-intelligence")
async def get_market_intelligence(
    user: AuthUser,
    cpv_prefix: str = Query("45", description="Prefix CPV np. '45' (budownictwo)"),
):
    """AI summary kondycji rynku zamówień dla danego CPV (TED + GUS + Pre-tender)."""
    try:
        engine = get_engine()
        stats: dict = {"cpv_prefix": cpv_prefix}

        with engine.connect() as conn:
            # TED count
            try:
                ted_count = conn.execute(text("""
                    SELECT COUNT(*), SUM(contract_value_eur) FROM ted_notices
                    WHERE EXISTS(SELECT 1 FROM unnest(cpv_codes) c WHERE c LIKE :pat)
                      AND publication_date >= CURRENT_DATE - INTERVAL '30 days'
                """), {"pat": f"{cpv_prefix}%"}).fetchone()
                stats["ted_30d"] = {"count": ted_count[0], "total_eur": float(ted_count[1] or 0)}
            except Exception:
                stats["ted_30d"] = {"count": 0, "total_eur": 0}

            # BZP count
            try:
                bzp_count = conn.execute(text("""
                    SELECT COUNT(*), SUM(awarded_value) FROM bzp_results
                    WHERE cpv_main LIKE :pat
                      AND publication_date >= CURRENT_DATE - INTERVAL '30 days'
                """), {"pat": f"{cpv_prefix}%"}).fetchone()
                stats["bzp_30d"] = {"count": bzp_count[0], "total_pln": float(bzp_count[1] or 0)}
            except Exception:
                stats["bzp_30d"] = {"count": 0, "total_pln": 0}

            # Pre-tender count
            try:
                pt_count = conn.execute(text("""
                    SELECT COUNT(*), SUM(estimated_value_pln) FROM pretender_signals
                    WHERE EXISTS(SELECT 1 FROM unnest(cpv_codes) c WHERE c LIKE :pat)
                """), {"pat": f"{cpv_prefix}%"}).fetchone()
                stats["pretenders"] = {"count": pt_count[0], "total_est_pln": float(pt_count[1] or 0)}
            except Exception:
                stats["pretenders"] = {"count": 0, "total_est_pln": 0}

            # GUS latest
            try:
                gus_row = conn.execute(text("""
                    SELECT unit_name, year, value FROM gus_indicators
                    WHERE variable_name ILIKE '%produkcja%'
                    ORDER BY year DESC, value DESC NULLS LAST LIMIT 1
                """)).fetchone()
                stats["gus_top"] = dict(gus_row._mapping) if gus_row else None
            except Exception:
                stats["gus_top"] = None

        # AI summary przez VLLMClient (Qwen → Bedrock → fallback)
        summary = _generate_market_summary(cpv_prefix, stats)
        return {"cpv_prefix": cpv_prefix, "stats": stats, "summary": summary}

    except Exception as e:
        logger.error("Market intelligence error: %s", e)
        return {"cpv_prefix": cpv_prefix, "stats": {}, "summary": f"Błąd: {e}"}


def _generate_market_summary(cpv_prefix: str, stats: dict) -> str:
    """Generuje AI summary — Qwen/vLLM → Bedrock → fallback tekstowy."""
    try:
        from services.ai.vllm_client import get_llm_client
        client = get_llm_client()

        prompt = (
            f"Na podstawie danych rynkowych dla CPV {cpv_prefix} (Polska, ostatnie 30 dni):\n"
            f"- Ogłoszenia TED (UE): {stats.get('ted_30d', {}).get('count', 0)} szt., "
            f"łączna wartość {stats.get('ted_30d', {}).get('total_eur', 0):,.0f} EUR\n"
            f"- Wyniki BZP (krajowe): {stats.get('bzp_30d', {}).get('count', 0)} szt., "
            f"łączna wartość {stats.get('bzp_30d', {}).get('total_pln', 0):,.0f} PLN\n"
            f"- Sygnały pre-przetargowe: {stats.get('pretenders', {}).get('count', 0)} szt., "
            f"szacowana wartość {stats.get('pretenders', {}).get('total_est_pln', 0):,.0f} PLN\n"
            f"- GUS top woj.: {stats.get('gus_top')}\n\n"
            f"Opisz kondycję rynku zamówień dla CPV {cpv_prefix} w Polsce. "
            f"Jakie trendy widać? Które regiony są najbardziej aktywne? "
            f"Co powinien wiedzieć wykonawca startując w przetargach z tego zakresu?"
        )
        return client.generate(prompt, max_tokens=1024)
    except Exception as e:
        logger.warning("AI summary failed: %s — returning static", e)
        ted = stats.get("ted_30d", {})
        bzp = stats.get("bzp_30d", {})
        pt = stats.get("pretenders", {})
        return (
            f"Podsumowanie rynku CPV {cpv_prefix} (ostatnie 30 dni): "
            f"TED: {ted.get('count', 0)} ogłoszeń UE ({ted.get('total_eur', 0):,.0f} EUR), "
            f"BZP: {bzp.get('count', 0)} wyników krajowych ({bzp.get('total_pln', 0):,.0f} PLN), "
            f"sygnały pre-przetargowe: {pt.get('count', 0)} szt. "
            f"[AI niedostępne — dane statystyczne]"
        )
