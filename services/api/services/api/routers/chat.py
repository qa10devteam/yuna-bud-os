"""M6 — Chat-brain structured edits for estimates.

POST /estimates/{id}/chat  → SSE stream
  - LLM proposes a structured edit: {op, target, value}
  - Deterministic code applies it and recomputes
  - audit_log row written on each change

SSE events: token | step | flag | done | error
Offline (StubClient): returns a deterministic canned edit sequence.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Generator

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from terra_db.session import get_engine
from services.ai.vllm_client import get_llm_client, VLLMClient, TERRA_SYSTEM_PROMPT

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    message: str



# Recognized ops for deterministic application
_VALID_OPS = {"set_param", "set_kp", "set_zysk", "set_robocizna"}


@router.post("/estimates/{estimate_id}/chat")
def estimate_chat(estimate_id: str, body: ChatRequest) -> StreamingResponse:
    """Chat-brain edits for an estimate. Returns SSE stream.

    Flow:
    1. LLM (StubClient offline) produces structured edit {op, target, value}
    2. Deterministic code applies the edit + recomputes
    3. Streams: step → flag (if any) → token (explanation) → done
    4. Writes audit_log row
    """
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, tender_id, variant, params FROM estimate WHERE id=:id"),
            {"id": estimate_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")

    tender_id = str(row[1])
    variant = row[2]
    current_params = row[3] or {}

    # Parse intent
    edit = _parse_edit_intent(body.message, current_params)

    return StreamingResponse(
        _stream_chat(engine, estimate_id, tender_id, variant, current_params, edit, body.message),
        media_type="text/event-stream",
    )


def _parse_edit_intent(message: str, current_params: dict) -> dict[str, Any]:
    """LLM → structured edit. In offline mode: deterministic regex + StubClient.

    Handles Polish commands like:
      "podnieś narzut do 15%"
      "ustaw zysk na 10%"
      "zmień robociznę na 40 zł/rg"
    """
    import re

    msg_lower = message.lower()

    # kp/narzut pattern: "podnieś narzut do 15%" / "ustaw kp na 12%"
    m = re.search(r"(?:narzut|kp|overhead)[^\d]*(\d+(?:[.,]\d+)?)\s*%", msg_lower)
    if m:
        return {"op": "set_param", "target": "kp_pct", "value": m.group(1).replace(",", ".")}

    # zysk/profit pattern
    m = re.search(r"(?:zysk|profit|marż)[^\d]*(\d+(?:[.,]\d+)?)\s*%", msg_lower)
    if m:
        return {"op": "set_param", "target": "zysk_pct", "value": m.group(1).replace(",", ".")}

    # robocizna pattern
    m = re.search(r"(?:robocizn|robociz)[^\d]*(\d+(?:[.,]\d+)?)", msg_lower)
    if m:
        return {"op": "set_param", "target": "robocizna_zl_rg", "value": m.group(1).replace(",", ".")}

    # Fallback: use LLM client
    llm = get_llm_client()
    prompt = (
        f"Przetlumacz polecenie na JSON: {message}\n"
        "Format: {\"op\": \"set_param\", \"target\": \"kp_pct|zysk_pct|robocizna_zl_rg\", \"value\": \"N\"}"
    )
    try:
        resp = llm.generate(prompt, json_mode=True)
        data = json.loads(resp)
        if data.get("op") in _VALID_OPS:
            return data
    except Exception:
        pass

    return {"op": "noop", "target": None, "value": None}


def _apply_edit(
    engine: Any, estimate_id: str, tender_id: str, variant: str,
    current_params: dict, edit: dict,
) -> dict[str, Any]:
    """Apply structured edit deterministically + recompute. Returns new params + total."""
    from decimal import Decimal
    from services.estimator import compute_variant_a, compute_variant_b, verify_sum_reconciliation, RateCard

    if edit.get("op") == "noop":
        return {"changed": False}

    new_params = dict(current_params)
    target = edit.get("target")
    value = edit.get("value")

    if target and value is not None:
        new_params[target] = str(value)

    # Recompute
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT przedmiar_items FROM analysis WHERE tender_id=:tid"),
            {"tid": tender_id},
        ).fetchone()
    if not row:
        return {"changed": False, "error": "no analysis"}

    items = row[0] or []

    if variant == "doc":
        est = compute_variant_a(items)
    else:
        rc = RateCard(
            kp_pct=Decimal(str(new_params.get("kp_pct", "12.0"))),
            zysk_pct=Decimal(str(new_params.get("zysk_pct", "8.0"))),
            robocizna_zl_rg=Decimal(str(new_params.get("robocizna_zl_rg", "35.0"))),
            calibration_coeff=Decimal(str(new_params.get("calibration_coeff", "1.00"))),
        )
        est = compute_variant_b(items, rate_card=rc)

    assert verify_sum_reconciliation(est), "Sum reconciliation failed after chat edit"

    with engine.begin() as conn:
        conn.execute(sa.text(
            "UPDATE estimate SET total_net_pln=:total, lines=cast(:lines as jsonb), "
            "params=cast(:params as jsonb) WHERE id=:id"
        ), {
            "id": estimate_id,
            "total": str(est.total_net_pln),
            "lines": json.dumps([l.to_dict() for l in est.lines]),
            "params": json.dumps(new_params),
        })

    return {
        "changed": True,
        "target": target,
        "value": value,
        "new_total": str(est.total_net_pln),
        "sum_reconciled": True,
    }


def _write_audit(engine: Any, estimate_id: str, tenant_id: str, edit: dict, result: dict) -> None:
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO audit_log (tenant_id, at, actor, action, entity, entity_id, detail) "
            "VALUES (:tid, now(), 'chat_brain', 'estimate_edit', 'estimate', cast(:eid as uuid), cast(:d as jsonb))"
        ), {
            "tid": tenant_id,
            "eid": estimate_id,
            "d": json.dumps({"edit": edit, "result": result}),
        })


def _stream_chat(
    engine: Any, estimate_id: str, tender_id: str, variant: str,
    current_params: dict, edit: dict, original_message: str,
) -> Generator[str, None, None]:
    """Generate SSE events."""

    def sse(event: str, data: Any) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    yield sse("step", {"message": f"Interpretuję polecenie: {original_message}"})

    if edit.get("op") == "noop":
        yield sse("flag", {"severity": "warn", "message": "Nie rozpoznano operacji — brak zmian"})
        yield sse("done", {"changed": False})
        return

    yield sse("step", {"message": f"Stosuję zmianę: {edit.get('target')} = {edit.get('value')}"})

    # Get tenant_id
    with engine.connect() as conn:
        trow = conn.execute(sa.text("SELECT tenant_id FROM tender WHERE id=:id"), {"id": tender_id}).fetchone()
    tenant_id = str(trow[0]) if trow else "unknown"

    result = _apply_edit(engine, estimate_id, tender_id, variant, current_params, edit)

    if result.get("error"):
        yield sse("error", {"message": result["error"]})
        return

    if result.get("changed"):
        yield sse("step", {"message": f"Nowa wartość kosztorysu: {result.get('new_total')} PLN"})
        yield sse("token", {"text": f"Parametr {edit.get('target')} zmieniony na {edit.get('value')}. "
                                    f"Kosztorys przeliczony: {result.get('new_total')} PLN netto."})
        _write_audit(engine, estimate_id, tenant_id, edit, result)

    yield sse("done", result)


# ─── Ogólny czat asystenta Terra.OS ───────────────────────────────────────────

class GeneralChatRequest(BaseModel):
    message: str
    tender_id: str | None = None
    context: str | None = None


@router.post("/chat")
def general_chat(body: GeneralChatRequest):
    """Ogólny asystent AXON — LLM-driven z fallbackiem na reguły."""
    from fastapi.responses import StreamingResponse as SR

    def stream():
        def sse(event, data):
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        # Build context-enriched prompt
        user_prompt = body.message
        if body.tender_id:
            user_prompt = f"[Kontekst: aktywny przetarg ID={body.tender_id}]\n{body.message}"
        if body.context:
            user_prompt = f"[Kontekst dodatkowy: {body.context}]\n{user_prompt}"

        llm = get_llm_client()

        # Try streaming if VLLMClient available
        if isinstance(llm, VLLMClient):
            try:
                for chunk in llm.generate_stream(user_prompt):
                    yield sse("token", {"text": chunk})
                yield sse("done", {"ok": True})
                return
            except Exception as e:
                # Fallback to non-streaming or rules
                try:
                    answer = llm.generate(user_prompt)
                    yield sse("token", {"text": answer})
                    yield sse("done", {"ok": True})
                    return
                except Exception:
                    pass  # Fall through to rule-based

        # Rule-based fallback (StubClient or server unreachable)
        msg = body.message.lower()

        if any(w in msg for w in ['przetarg', 'ofert', 'kosztorys', 'wycen']):
            answer = (
                "W systemie AXON|TERRA masz dostep do przetargow z BZP. "
                "Uzyj modulu **Zwiad** aby przefiltrowac liste, kliknij przetarg aby pobrac dokumentacje, "
                "nastepnie **Kosztorys** aby porownac warianty doc/owner, a **Silnik** aby ocenic ryzyko Monte Carlo."
            )
        elif any(w in msg for w in ['ryzyko', 'silnik', 'analiz', 'monte']):
            answer = (
                "Silnik decyzyjny analizuje wykonalnosc na 3 poziomach: "
                "**L1** - reguly twarde (blokery), "
                "**L2** - ryzyko Monte Carlo (2000 probek, marze P10/P50/P90), "
                "**L3** - wyjasnienie decyzji."
            )
        elif any(w in msg for w in ['pomoc', 'jak', 'help', 'co to', 'co umiesz']):
            answer = (
                "AXON|TERRA - system wsparcia decyzji dla wykonawcow robot budowlanych. "
                "**Flow:** Zwiad (lista BZP) -> Kosztorys (2 warianty) -> Silnik (ryzyko) -> Decyzja (GO/NO-GO)."
            )
        else:
            answer = (
                "Jestem asystentem AXON|TERRA. Pomagam w analizie przetargow budowlanych, "
                "kosztorysowaniu i ocenie ryzyka. "
                "Zadaj konkretne pytanie np. 'jak dziala kosztorys?' lub 'co to jest marza P50?'"
            )

        yield sse("token", {"text": answer})
        yield sse("done", {"ok": True})

    return SR(stream(), media_type="text/event-stream")
