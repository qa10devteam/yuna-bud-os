"""
S94/S95/S96 — Automation Core: Condition builder, Action library, Trigger library.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ─── S94: Condition Builder ────────────────────────────────────────────────────

class ConditionOperator(str, Enum):
    EQ = "eq"
    GT = "gt"
    LT = "lt"
    CONTAINS = "contains"
    IN_LIST = "in_list"


class AutomationCondition(BaseModel):
    field: str
    operator: ConditionOperator
    value: Any


def evaluate_condition(tender: dict, condition: AutomationCondition) -> bool:
    """Evaluate a single condition against a tender dict. S94."""
    raw = tender.get(condition.field)
    val = condition.value

    op = condition.operator
    try:
        if op == ConditionOperator.EQ:
            return str(raw) == str(val)
        elif op == ConditionOperator.GT:
            return float(raw or 0) > float(val)
        elif op == ConditionOperator.LT:
            return float(raw or 0) < float(val)
        elif op == ConditionOperator.CONTAINS:
            return str(val).lower() in str(raw or "").lower()
        elif op == ConditionOperator.IN_LIST:
            lst = val if isinstance(val, list) else [val]
            return str(raw) in [str(v) for v in lst]
    except Exception as e:
        logger.debug("evaluate_condition error field=%s op=%s: %s", condition.field, op, e)
    return False


def evaluate_conditions(tender: dict, conditions: list[AutomationCondition], logic: str = "AND") -> bool:
    """Evaluate list of conditions with AND/OR logic."""
    if not conditions:
        return True
    results = [evaluate_condition(tender, c) for c in conditions]
    if logic.upper() == "OR":
        return any(results)
    return all(results)


# ─── S95: Action Library ───────────────────────────────────────────────────────

class ActionType(str, Enum):
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    BOOKMARK = "BOOKMARK"
    DECISION = "DECISION"
    NOTIFICATION = "NOTIFICATION"


def execute_action(action_type: ActionType, params: dict, context: dict) -> dict:
    """Execute an automation action. S95."""
    tender_id = context.get("tender_id")
    tenant_id = context.get("tenant_id")
    result = {"action": action_type, "tender_id": tender_id, "status": "ok"}

    try:
        if action_type == ActionType.EMAIL:
            # Log only — real SMTP handled by notifications module
            logger.info("AUTO EMAIL to=%s subject=%s tender=%s", params.get("to"), params.get("subject"), tender_id)
            result["detail"] = "email_logged"

        elif action_type == ActionType.WEBHOOK:
            import httpx
            url = params.get("url", "")
            if url:
                payload = {**params.get("payload", {}), "tender_id": tender_id, "tenant_id": tenant_id}
                try:
                    with httpx.Client(timeout=5.0) as c:
                        r = c.post(url, json=payload)
                    result["http_status"] = r.status_code
                except Exception as e:
                    result["status"] = "error"
                    result["detail"] = str(e)
            else:
                result["status"] = "skip"
                result["detail"] = "no url"

        elif action_type == ActionType.BOOKMARK:
            from terra_db.session import get_engine
            import sqlalchemy as sa, uuid as _uuid
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(sa.text("""
                    INSERT INTO tender_bookmark (id, tender_id, tenant_id, created_at)
                    VALUES (gen_random_uuid(), :tid, :tnid, NOW())
                    ON CONFLICT DO NOTHING
                """), {"tid": tender_id, "tnid": tenant_id})
                conn.commit()
            result["detail"] = "bookmarked"

        elif action_type == ActionType.DECISION:
            from terra_db.session import get_engine
            import sqlalchemy as sa
            decision_val = params.get("decision", "bid")
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(sa.text("""
                    UPDATE tender SET decision = :d WHERE id = :tid::uuid
                """), {"d": decision_val, "tid": tender_id})
                conn.commit()
            result["detail"] = f"decision={decision_val}"

        elif action_type == ActionType.NOTIFICATION:
            from terra_db.session import get_engine
            import sqlalchemy as sa
            msg = params.get("message", "Automation notification")
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(sa.text("""
                    INSERT INTO notifications (id, tenant_id, type, message, created_at, read)
                    VALUES (gen_random_uuid(), :tnid, 'automation', :msg, NOW(), FALSE)
                """), {"tnid": tenant_id, "msg": msg})
                conn.commit()
            result["detail"] = "notification_created"

    except Exception as e:
        logger.exception("execute_action %s failed: %s", action_type, e)
        result["status"] = "error"
        result["detail"] = str(e)

    return result


# ─── S96: Trigger Library ──────────────────────────────────────────────────────

class TriggerEvent(str, Enum):
    TENDER_CREATED = "TENDER_CREATED"
    SCORE_UPDATED = "SCORE_UPDATED"
    DEADLINE_7D = "DEADLINE_7D"
    DEADLINE_3D = "DEADLINE_3D"
    DEADLINE_1D = "DEADLINE_1D"
    DECISION_MADE = "DECISION_MADE"
    MANUAL = "MANUAL"


# Registry: event → list of handler callables
_HANDLERS: dict[str, list] = {}


def register_handler(event: TriggerEvent, handler) -> None:
    """Register a handler for a trigger event."""
    key = event.value
    if key not in _HANDLERS:
        _HANDLERS[key] = []
    _HANDLERS[key].append(handler)


def dispatch_trigger(event: TriggerEvent, context: dict) -> list[dict]:
    """Dispatch trigger to all registered handlers. Returns list of results."""
    key = event.value
    handlers = _HANDLERS.get(key, [])
    results = []
    for h in handlers:
        try:
            r = h(context)
            results.append(r or {"status": "ok"})
        except Exception as e:
            logger.exception("trigger handler %s/%s error: %s", key, h, e)
            results.append({"status": "error", "detail": str(e)})
    logger.info("dispatch_trigger %s: %d handlers, %d results", key, len(handlers), len(results))
    return results
