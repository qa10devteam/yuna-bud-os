"""LangGraph pipeline v1 + v2 — Zwiad → Analiza → Scoring → AHP → Decyzja → Brief.

Fazy 7.03 (v1) + 7.04 (v2).
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import sqlalchemy as sa

from langgraph.graph import END, StateGraph
from typing import TypedDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    tenant_id: str
    tender_id: str
    tender_data: dict
    documents: list
    analysis: dict          # key_facts, red_flags, summary_md
    score: float
    score_breakdown: dict
    agent_run_id: str
    error: str
    steps: list
    # v2 extensions
    ahp_result: dict
    competitor_data: list
    bid_strategy: dict
    decision_brief: str
    go_decision: str        # GO / NO-GO / CONSIDER
    icb_pricing: dict       # InterCenBud pricing data
    icb_estimate: dict      # ICB quick estimate from node_icb_estimate


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------

def _get_engine():
    from terra_db.session import get_engine
    return get_engine()


def _run_query(sql: str, params: dict | None = None) -> list[dict]:
    """Execute a SELECT and return list of row dicts."""
    engine = _get_engine()
    with engine.connect() as conn:
        result = conn.execute(sa.text(sql), params or {})
        keys = list(result.keys())
        return [dict(zip(keys, row)) for row in result.fetchall()]


def _run_exec(sql: str, params: dict | None = None) -> None:
    """Execute DML (INSERT/UPDATE)."""
    engine = _get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text(sql), params or {})


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _get_llm():
    from services.ai.vllm_client import VLLMClient
    return VLLMClient(base_url="http://localhost:8001/v1", model="axon", timeout=60.0)


def _llm_generate(prompt: str, system: str = "", json_mode: bool = False) -> str:
    try:
        llm = _get_llm()
        return llm.generate(prompt, system=system, json_mode=json_mode)
    except Exception as exc:
        logger.error("LLM generate failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# NODE 1: fetch_tender
# ---------------------------------------------------------------------------

def node_fetch_tender(state: AgentState) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append("fetch_tender")
    tender_id = state.get("tender_id")
    if not tender_id:
        return {**state, "steps": steps, "error": "fetch_tender: brak tender_id"}
    try:
        rows = _run_query(
            "SELECT * FROM tender WHERE id = :tid",
            {"tid": tender_id},
        )
        if not rows:
            return {**state, "steps": steps, "error": f"fetch_tender: tender {tender_id} nie znaleziony"}
        tender_data = rows[0]
        # Convert non-serialisable types
        for k, v in tender_data.items():
            if isinstance(v, datetime):
                tender_data[k] = v.isoformat()
            elif hasattr(v, "__str__") and not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                tender_data[k] = str(v)

        # Fetch documents
        docs = _run_query(
            "SELECT id, file_name, content_text FROM tender_document WHERE tender_id = :tid LIMIT 20",
            {"tid": tender_id},
        )
        logger.info("fetch_tender: tender_id=%s docs=%d", tender_id, len(docs))
        return {**state, "steps": steps, "tender_data": tender_data, "documents": docs}
    except Exception as exc:
        logger.exception("fetch_tender error")
        return {**state, "steps": steps, "error": f"fetch_tender: {exc}"}


# ---------------------------------------------------------------------------
# NODE 2: analyze_swz
# ---------------------------------------------------------------------------

def node_analyze_swz(state: AgentState) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append("analyze_swz")
    if state.get("error"):
        return {**state, "steps": steps}

    tender_data = state.get("tender_data", {})
    documents = state.get("documents", [])
    tender_id = state.get("tender_id", "")

    # Build context for LLM
    ctx_parts = [
        f"Przetarg: {tender_data.get('title', '—')}",
        f"Zamawiający: {tender_data.get('buyer', '—')}",
        f"Wartość: {tender_data.get('value_pln', '—')} PLN",
        f"CPV: {tender_data.get('cpv', [])}",
        f"Termin: {tender_data.get('deadline_at', '—')}",
    ]
    if documents:
        for doc in documents[:3]:
            txt = (doc.get("content_text") or "")[:1500]
            if txt:
                ctx_parts.append(f"\n--- Dokument: {doc.get('file_name', '')} ---\n{txt}")
    else:
        raw = tender_data.get("raw") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}
        raw_txt = json.dumps(raw, ensure_ascii=False)[:2000]
        ctx_parts.append(f"\nRaw data: {raw_txt}")

    context_str = "\n".join(ctx_parts)

    system = (
        "Jesteś ekspertem analizy przetargów publicznych. "
        "Odpowiadasz WYŁĄCZNIE poprawnym JSON bez markdown."
    )
    prompt = (
        f"Przeanalizuj poniższy przetarg i zwróć JSON z kluczami:\n"
        f"- key_facts: obiekt z faktami (wartość, termin, wymagania)\n"
        f"- red_flags: lista stringów z ryzykami\n"
        f"- summary_md: krótkie podsumowanie w Markdown (max 300 znaków)\n\n"
        f"Dane przetargu:\n{context_str}\n\n"
        f"Zwróć TYLKO JSON, bez komentarzy."
    )

    try:
        raw_resp = _llm_generate(prompt, system=system, json_mode=True)
        try:
            parsed = json.loads(raw_resp)
        except json.JSONDecodeError:
            import re
            m = re.search(r"\{.*\}", raw_resp, re.DOTALL)
            parsed = json.loads(m.group(0)) if m else {}
        analysis = {
            "key_facts": parsed.get("key_facts", {}),
            "red_flags": parsed.get("red_flags", []),
            "summary_md": parsed.get("summary_md", "Brak podsumowania."),
        }
    except Exception as exc:
        logger.warning("analyze_swz LLM failed (%s), using fallback", exc)
        analysis = {
            "key_facts": {"title": tender_data.get("title", "")},
            "red_flags": [],
            "summary_md": f"Przetarg: {tender_data.get('title', '')}",
        }

    # Upsert analysis table
    try:
        analysis_id = str(uuid.uuid4())
        _run_exec(
            """
            INSERT INTO analysis (id, tender_id, summary_md, red_flags, key_facts, created_at)
            VALUES (:id, :tid, :summary, :red_flags, :key_facts, now())
            ON CONFLICT (tender_id)
            DO UPDATE SET summary_md=EXCLUDED.summary_md,
                          red_flags=EXCLUDED.red_flags,
                          key_facts=EXCLUDED.key_facts
            """,
            {
                "id": analysis_id,
                "tid": tender_id,
                "summary": analysis["summary_md"],
                "red_flags": json.dumps(analysis["red_flags"]),
                "key_facts": json.dumps(analysis["key_facts"]),
            },
        )
    except Exception as exc:
        logger.warning("analyze_swz: nie zapisano do analysis table: %s", exc)

    return {**state, "steps": steps, "analysis": analysis}


# ---------------------------------------------------------------------------
# NODE 3: score_tender
# ---------------------------------------------------------------------------

def node_score_tender(state: AgentState) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append("score_tender")
    if state.get("error"):
        return {**state, "steps": steps}

    tender_id = state.get("tender_id", "")
    tenant_id = state.get("tenant_id", "")
    tender_data = state.get("tender_data", {})

    # Load scoring_config
    cfg_rows = _run_query(
        "SELECT * FROM scoring_config WHERE tenant_id = :tid LIMIT 1",
        {"tid": tenant_id},
    ) if tenant_id else []
    cfg = cfg_rows[0] if cfg_rows else {}

    cpv_weight        = float(cfg.get("cpv_weight",        0.35))
    value_weight      = float(cfg.get("value_weight",      0.20))
    region_weight     = float(cfg.get("region_weight",     0.15))
    deadline_weight   = float(cfg.get("deadline_weight",   0.10))
    hist_win_weight   = float(cfg.get("historical_win_weight", 0.20))
    preferred_cpvs    = cfg.get("preferred_cpvs", []) or []
    preferred_regions = cfg.get("preferred_regions", []) or []
    min_value         = float(cfg.get("min_value_pln") or 0)
    max_value         = float(cfg.get("max_value_pln") or 1e12)

    breakdown: dict[str, float] = {}

    # CPV match
    tender_cpvs = tender_data.get("cpv") or []
    if isinstance(tender_cpvs, str):
        try:
            tender_cpvs = json.loads(tender_cpvs)
        except Exception:
            tender_cpvs = [tender_cpvs]
    if preferred_cpvs:
        matches = sum(
            1 for tc in tender_cpvs
            for pc in preferred_cpvs
            if tc.startswith(pc[:5])
        )
        cpv_score = min(1.0, matches / max(1, len(preferred_cpvs)))
    else:
        cpv_score = 0.5
    breakdown["cpv"] = round(cpv_score * cpv_weight, 4)

    # Value fit
    value_pln = float(tender_data.get("value_pln") or 0)
    if value_pln == 0:
        value_score = 0.5
    elif min_value <= value_pln <= max_value:
        value_score = 1.0
    elif value_pln < min_value:
        value_score = max(0.0, value_pln / max(1, min_value))
    else:
        value_score = max(0.0, 1 - (value_pln - max_value) / max(1, max_value))
    breakdown["value"] = round(value_score * value_weight, 4)

    # Region match
    voivodeship = (tender_data.get("voivodeship") or "").lower()
    if preferred_regions:
        region_match = any(voivodeship in r.lower() or r.lower() in voivodeship for r in preferred_regions)
        region_score = 1.0 if region_match else 0.3
    else:
        region_score = 0.5
    breakdown["region"] = round(region_score * region_weight, 4)

    # Deadline bonus (farther deadline = better)
    deadline_score = 0.5
    try:
        dl_str = tender_data.get("deadline_at")
        if dl_str:
            dl = datetime.fromisoformat(str(dl_str).replace("Z", "+00:00"))
            days_left = (dl - datetime.now(timezone.utc)).days
            deadline_score = min(1.0, max(0.0, days_left / 30))
    except Exception:
        pass
    breakdown["deadline"] = round(deadline_score * deadline_weight, 4)

    # Historical win (placeholder — no CPV join available easily)
    hist_score = 0.5
    breakdown["historical_win"] = round(hist_score * hist_win_weight, 4)

    total_score = round(sum(breakdown.values()), 4)

    # Update tender
    try:
        _run_exec(
            "UPDATE tender SET match_score = :score WHERE id = :tid",
            {"score": total_score, "tid": tender_id},
        )
    except Exception as exc:
        logger.warning("score_tender: UPDATE tender failed: %s", exc)

    return {**state, "steps": steps, "score": total_score, "score_breakdown": breakdown}


# ---------------------------------------------------------------------------
# NODE 3b: icb_estimate — quick ICB cost estimate from tender title
# ---------------------------------------------------------------------------

def node_icb_estimate(state: AgentState) -> AgentState:
    """Estymuj koszt realizacji z ICB + dodaj do kontekstu."""
    steps = list(state.get('steps', []))
    steps.append('icb_estimate')
    tender = state.get('tender_data', {})

    try:
        from services.api.services.api.intelligence.icb_service import (
            search_icb, get_latest_quarter, get_narzuty
        )
        rok, nr = get_latest_quarter()
        title = tender.get('title', '') or ''

        # Search ICB for relevant materials based on tender title
        matches = search_icb(title[:80], kwartalrok=rok, kwartalnr=nr, limit=5) if title else []

        # Get narzuty for markup estimate
        narzuty = get_narzuty(rok, nr)

        icb_context = {
            'quarter': f'{rok}-Q{nr}',
            'relevant_materials': matches[:5],
            'narzuty_sample': narzuty[:3] if narzuty else [],
        }

        # Store in state - merge with existing analysis
        analysis = state.get('analysis', {})
        analysis['icb_estimate'] = icb_context
        state = {**state, 'analysis': analysis, 'steps': steps, 'icb_estimate': icb_context}
        logger.info(f'ICB estimate: {len(matches)} materials found for tender {tender.get("id")}')
    except Exception as e:
        logger.warning(f'ICB estimate failed: {e}')
        steps.append(f'icb_estimate_error:{e}')
        state = {**state, 'steps': steps}

    return state


# ---------------------------------------------------------------------------
# NODE 4: ahp_eval
# ---------------------------------------------------------------------------

def node_ahp_eval(state: AgentState) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append("ahp_eval")
    if state.get("error"):
        return {**state, "steps": steps}

    score = state.get("score", 0.0)
    breakdown = state.get("score_breakdown", {})
    tenant_id = state.get("tenant_id", "")

    # Load weights from scoring_config
    cfg_rows = _run_query(
        "SELECT * FROM scoring_config WHERE tenant_id = :tid LIMIT 1",
        {"tid": tenant_id},
    ) if tenant_id else []
    cfg = cfg_rows[0] if cfg_rows else {}

    weights = {
        "cpv":            float(cfg.get("cpv_weight",        0.35)),
        "value":          float(cfg.get("value_weight",      0.20)),
        "region":         float(cfg.get("region_weight",     0.15)),
        "deadline":       float(cfg.get("deadline_weight",   0.10)),
        "historical_win": float(cfg.get("historical_win_weight", 0.20)),
    }

    # AHP consistency ratio (simplified 5-criterion pairwise)
    # Build pairwise comparison matrix from weights
    w_vals = list(weights.values())
    n = len(w_vals)
    w_sum = sum(w_vals) or 1.0
    w_norm = [w / w_sum for w in w_vals]

    # Lambda_max = sum(A*w / w) — approximated
    lambda_max = n  # perfect consistency assumption when weights are given directly
    ci = (lambda_max - n) / max(1, n - 1)
    ri_table = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32}
    ri = ri_table.get(n, 1.12)
    cr = ci / ri if ri > 0 else 0.0

    # Decision
    if score >= 0.70:
        go_decision = "GO"
    elif score >= 0.40:
        go_decision = "CONSIDER"
    else:
        go_decision = "NO-GO"

    ahp_result = {
        "go_decision": go_decision,
        "consistency_ratio": round(cr, 4),
        "weights": weights,
        "final_score": score,
    }

    return {**state, "steps": steps, "ahp_result": ahp_result, "go_decision": go_decision}


# ---------------------------------------------------------------------------
# NODE 5: competitor_check
# ---------------------------------------------------------------------------

def node_competitor_check(state: AgentState) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append("competitor_check")
    if state.get("error"):
        return {**state, "steps": steps}

    tender_data = state.get("tender_data", {})
    tender_cpvs = tender_data.get("cpv") or []
    if isinstance(tender_cpvs, str):
        try:
            tender_cpvs = json.loads(tender_cpvs)
        except Exception:
            tender_cpvs = [tender_cpvs]

    cpv_prefix = ""
    if tender_cpvs:
        cpv_prefix = str(tender_cpvs[0])[:5] if tender_cpvs[0] else ""

    try:
        if cpv_prefix:
            rows = _run_query(
                """
                SELECT nip, name, city, province, win_rate, total_wins, total_value, top_cpv
                FROM atlas_contractors
                WHERE top_cpv::text LIKE :cpv_like
                ORDER BY win_rate DESC NULLS LAST
                LIMIT 5
                """,
                {"cpv_like": f"%{cpv_prefix}%"},
            )
        else:
            rows = _run_query(
                """
                SELECT nip, name, city, province, win_rate, total_wins, total_value, top_cpv
                FROM atlas_contractors
                ORDER BY win_rate DESC NULLS LAST
                LIMIT 5
                """,
            )
        # Serialise
        for row in rows:
            for k, v in row.items():
                if not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                    row[k] = str(v)
        competitor_data = rows
    except Exception as exc:
        logger.warning("competitor_check: %s", exc)
        competitor_data = []

    return {**state, "steps": steps, "competitor_data": competitor_data}


# ---------------------------------------------------------------------------
# NODE 6: bid_strategy
# ---------------------------------------------------------------------------

def node_bid_strategy(state: AgentState) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append("bid_strategy")
    if state.get("error"):
        return {**state, "steps": steps}

    tenant_id = state.get("tenant_id", "")
    tender_data = state.get("tender_data", {})
    tender_cpvs = tender_data.get("cpv") or []

    try:
        rows = _run_query(
            """
            SELECT markup_pct, won, bid_date, our_price, winning_price
            FROM bid_intelligence
            WHERE tenant_id = :tid
            ORDER BY bid_date DESC
            LIMIT 20
            """,
            {"tid": tenant_id},
        ) if tenant_id else []

        if rows:
            markups = [float(r["markup_pct"] or 0) for r in rows if r.get("markup_pct")]
            wins = [r for r in rows if r.get("won")]
            avg_markup = round(sum(markups) / len(markups), 2) if markups else 10.0
            win_rate = round(len(wins) / len(rows), 4) if rows else 0.5
            price_ratios = [
                float(r["our_price"]) / float(r["winning_price"])
                for r in rows
                if r.get("our_price") and r.get("winning_price") and float(r["winning_price"]) > 0
            ]
            avg_price_ratio = round(sum(price_ratios) / len(price_ratios), 4) if price_ratios else 1.05
        else:
            avg_markup = 10.0
            win_rate = 0.5
            avg_price_ratio = 1.05

        recommended_markup = max(5.0, avg_markup * (1 + (0.5 - win_rate) * 0.2))

        bid_strategy = {
            "recommended_markup": round(recommended_markup, 2),
            "expected_win_prob": win_rate,
            "historical_avg_markup": avg_markup,
            "avg_price_ratio": avg_price_ratio,
            "sample_size": len(rows),
        }
    except Exception as exc:
        logger.warning("bid_strategy: %s", exc)
        bid_strategy = {
            "recommended_markup": 10.0,
            "expected_win_prob": 0.5,
            "historical_avg_markup": 10.0,
            "avg_price_ratio": 1.05,
            "sample_size": 0,
        }

    return {**state, "steps": steps, "bid_strategy": bid_strategy}


# ---------------------------------------------------------------------------
# NODE 7: generate_brief
# ---------------------------------------------------------------------------

def node_generate_brief(state: AgentState) -> AgentState:
    steps = list(state.get("steps", []))
    steps.append("generate_brief")
    if state.get("error"):
        return {**state, "steps": steps}

    tender_data = state.get("tender_data", {})
    analysis = state.get("analysis", {})
    ahp_result = state.get("ahp_result", {})
    competitor_data = state.get("competitor_data", [])
    bid_strategy = state.get("bid_strategy", {})
    go_decision = state.get("go_decision", "CONSIDER")
    score = state.get("score", 0.0)

    competitors_txt = "\n".join(
        f"- {c.get('name', '?')} ({c.get('city', '')}, win_rate={c.get('win_rate', 0):.0%})"
        for c in (competitor_data or [])[:5]
    ) or "Brak danych o konkurentach."

    prompt = f"""Jesteś doradcą decyzyjnym. Wygeneruj raport decyzyjny (Decision Brief) dla przetargu.

## Dane przetargu
- Tytuł: {tender_data.get('title', '—')}
- Zamawiający: {tender_data.get('buyer', '—')}
- Wartość: {tender_data.get('value_pln', '—')} PLN
- CPV: {tender_data.get('cpv', [])}
- Termin: {tender_data.get('deadline_at', '—')}

## Analiza
{analysis.get('summary_md', '—')}

Red flags:
{chr(10).join('- ' + f for f in analysis.get('red_flags', [])) or '— brak red flags'}

## Scoring
- Wynik ogólny: {score:.2%}
- Decyzja AHP: **{go_decision}**
- Współczynnik spójności AHP: {ahp_result.get('consistency_ratio', 0):.3f}

## Konkurenci (top 5 wg CPV)
{competitors_txt}

## Strategia ofertowa
- Rekomendowany narzut: {bid_strategy.get('recommended_markup', 10):.1f}%
- Historyczna skuteczność: {bid_strategy.get('expected_win_prob', 0):.0%}
- Próbka historyczna: {bid_strategy.get('sample_size', 0)} ofert

Wygeneruj Decision Brief w Markdown (max 400 słów) z sekcjami:
1. Podsumowanie wykonawcze
2. Kluczowe ryzyka
3. Rekomendacja ({go_decision}) z uzasadnieniem
4. Proponowane działania
"""

    try:
        decision_brief = _llm_generate(prompt, system="Jesteś ekspertem przetargów budowlanych. Piszesz po polsku.")
        if not decision_brief:
            decision_brief = f"# Decision Brief\n\n**Decyzja: {go_decision}**\n\nWynik scoringowy: {score:.2%}\n"
    except Exception as exc:
        logger.warning("generate_brief LLM failed: %s", exc)
        decision_brief = f"# Decision Brief\n\n**Decyzja: {go_decision}**\n\nWynik scoringowy: {score:.2%}\n"

    return {**state, "steps": steps, "decision_brief": decision_brief, "go_decision": go_decision}


# ---------------------------------------------------------------------------
# NODE 8: icb_pricing — wycena materiałów z InterCenBud
# ---------------------------------------------------------------------------

def node_icb_pricing(state: AgentState) -> AgentState:
    """Dodaj kalkulację kosztów materiałów z ICB (784k rekordów).

    Analizuje CPV tendera, dopasowuje kategorie ICB, pobiera aktualne ceny
    i dodaje podsumowanie kosztowe do state.
    """
    steps = list(state.get("steps", []))
    steps.append("icb_pricing")
    if state.get("error"):
        return {**state, "steps": steps}

    tender_data = state.get("tender_data", {})
    analysis = state.get("analysis", {})

    # Map CPV codes to ICB categories
    cpv_to_icb = {
        "45": "murarstwo",       # Construction work
        "4521": "murarstwo",     # Building construction
        "4522": "dach_pokrycia", # Roof works
        "4523": "nawierzchnie",  # Highway, road
        "4524": "instalacje_wod_kan",  # Water works
        "4525": "kruszywa_ziemne",     # Construction for mining
        "4431": "plytki_ceramiczne",   # Floor covering
        "4432": "malowanie",           # Painting
        "4433": "instalacje_wod_kan",  # Plumbing
        "4434": "elektryka",           # Electrical
        "4411": "stal_konstrukcyjna",  # Structural steel
        "4412": "izolacja_termo",      # Insulation
    }

    tender_cpvs = tender_data.get("cpv") or []
    if isinstance(tender_cpvs, str):
        try:
            import json as _json
            tender_cpvs = _json.loads(tender_cpvs)
        except Exception:
            tender_cpvs = [tender_cpvs]

    # Determine relevant categories
    categories = set()
    for cpv in tender_cpvs:
        cpv_str = str(cpv).replace(".", "")
        for prefix, cat in cpv_to_icb.items():
            if cpv_str.startswith(prefix):
                categories.add(cat)
                break

    if not categories:
        # Fallback: use all major construction categories
        categories = {"murarstwo", "stal_konstrukcyjna", "kruszywa_ziemne", "instalacje_wod_kan"}

    try:
        from services.api.services.api.intelligence.icb_service import (
            get_latest_quarter, get_all_narzuty, get_regional_coefficient,
        )
        from services.api.services.api.intelligence.price_intelligence import (
            get_material_risk_score,
        )

        rok, nr = get_latest_quarter()

        # Get average prices per category
        category_prices = {}
        category_risks = {}
        for cat in categories:
            rows = _run_query("""
                SELECT ROUND(AVG(cena_netto)::numeric, 2) as avg_price,
                       ROUND(MIN(cena_netto)::numeric, 2) as min_price,
                       ROUND(MAX(cena_netto)::numeric, 2) as max_price,
                       COUNT(*) as n
                FROM icb_ceny_srednie
                WHERE category = :cat AND typ_rms = 'M'
                  AND kwartalrok = :rok AND kwartalnr = :nr AND cena_netto > 0
            """, {"cat": cat, "rok": rok, "nr": nr})
            if rows and rows[0]["avg_price"]:
                category_prices[cat] = rows[0]

            # Risk assessment
            risk = get_material_risk_score(cat)
            category_risks[cat] = risk

        # Get narzuty for the region
        region = tender_data.get("region", "mazowieckie")
        regional_coeff = get_regional_coefficient(region, "Ogolne", rok, nr)
        narzuty = get_all_narzuty(rok, nr)

        # Build ICB pricing context
        icb_pricing = {
            "quarter": f"{rok}-Q{nr}",
            "categories_analyzed": list(categories),
            "regional_coefficient": regional_coeff,
            "region": region,
            "category_prices": category_prices,
            "material_risks": {
                cat: {"score": r.get("score", 0), "level": r.get("level", "unknown"), "trend": r.get("trend", "stable")}
                for cat, r in category_risks.items()
            },
            "narzuty_summary": {
                "koszty_posrednie": narzuty[0]["koszty_posrednie"] if narzuty else 65.0,
                "zysk": narzuty[0]["zysk"] if narzuty else 10.0,
                "koszty_zakupu": narzuty[0]["koszty_zakupu"] if narzuty else 12.0,
            } if narzuty else {},
            "high_risk_materials": [
                cat for cat, r in category_risks.items()
                if r.get("level") == "high"
            ],
        }

    except Exception as exc:
        logger.warning("icb_pricing: %s", exc)
        icb_pricing = {"error": str(exc), "categories_analyzed": list(categories)}

    return {**state, "steps": steps, "icb_pricing": icb_pricing}


# ---------------------------------------------------------------------------
# Graph v1 — Zwiad + Analiza + Scoring
# ---------------------------------------------------------------------------

def _build_graph_v1() -> Any:
    g = StateGraph(AgentState)
    g.add_node("fetch_tender", node_fetch_tender)
    g.add_node("analyze_swz", node_analyze_swz)
    g.add_node("score_tender", node_score_tender)
    g.add_node("icb_estimate", node_icb_estimate)
    g.set_entry_point("fetch_tender")
    g.add_edge("fetch_tender", "analyze_swz")
    g.add_edge("analyze_swz", "score_tender")
    g.add_edge("score_tender", "icb_estimate")
    g.add_edge("icb_estimate", END)
    return g.compile()


def _build_graph_v2() -> Any:
    g = StateGraph(AgentState)
    g.add_node("fetch_tender",    node_fetch_tender)
    g.add_node("analyze_swz",     node_analyze_swz)
    g.add_node("score_tender",    node_score_tender)
    g.add_node("icb_estimate",    node_icb_estimate)
    g.add_node("ahp_eval",        node_ahp_eval)
    g.add_node("competitor_check", node_competitor_check)
    g.add_node("bid_strategy",    node_bid_strategy)
    g.add_node("icb_pricing",     node_icb_pricing)
    g.add_node("generate_brief",  node_generate_brief)
    g.set_entry_point("fetch_tender")
    g.add_edge("fetch_tender",    "analyze_swz")
    g.add_edge("analyze_swz",     "score_tender")
    g.add_edge("score_tender",    "icb_estimate")
    g.add_edge("icb_estimate",    "ahp_eval")
    g.add_edge("ahp_eval",        "competitor_check")
    g.add_edge("competitor_check","bid_strategy")
    g.add_edge("bid_strategy",    "icb_pricing")
    g.add_edge("icb_pricing",     "generate_brief")
    g.add_edge("generate_brief",  END)
    return g.compile()


# Compiled graphs (lazy singletons)
_app_v1 = None
_app_v2 = None


def get_app_v1():
    global _app_v1
    if _app_v1 is None:
        _app_v1 = _build_graph_v1()
    return _app_v1


def get_app_v2():
    global _app_v2
    if _app_v2 is None:
        _app_v2 = _build_graph_v2()
    return _app_v2
