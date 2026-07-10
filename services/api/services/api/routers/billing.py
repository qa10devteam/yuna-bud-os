"""Faza 76-80 — Billing / Stripe integration.

Endpoints:
  GET  /api/v2/billing/plans          — list available plans (hardcoded, public)
  POST /api/v2/billing/checkout       — create Stripe checkout session (or placeholder)
  GET  /api/v2/billing/subscription   — current org plan + full status (requires auth)
  POST /api/v2/billing/cancel         — cancel subscription (requires auth)
  POST /api/v2/billing/webhook        — Stripe webhook handler (no auth — verified by sig)
"""
from __future__ import annotations


import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/billing", tags=["billing"])


# ─── DB dependency ─────────────────────────────────────────────────────────────

def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


# ─── Plans catalog ─────────────────────────────────────────────────────────────

PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price_pln": 0,
        "price_label": "0 PLN",
        "billing": "bezpłatny",
        "stripe_price_id": None,
        "limits": {
            "tenders": 5,
            "ai_analysis": False,
            "team_members": 1,
            "api_access": False,
        },
        "features": [
            "Do 5 przetargów",
            "Ręczne zarządzanie",
            "Podstawowe raporty",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_pln": 499,
        "price_label": "499 PLN/mies",
        "billing": "miesięcznie",
        "popular": True,
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_pro_placeholder"),
        "limits": {
            "tenders": 50,
            "ai_analysis": True,
            "team_members": 5,
            "api_access": False,
        },
        "features": [
            "Do 50 przetargów",
            "AI analiza ryzyka SWZ",
            "Automatyczny BZP sync",
            "Silnik kalkulacji",
            "5 członków zespołu",
            "Eksport Excel/PDF",
        ],
    },
    {
        "id": "business",
        "name": "Business",
        "price_pln": 1499,
        "price_label": "1499 PLN/mies",
        "billing": "miesięcznie",
        "stripe_price_id": os.getenv("STRIPE_PRICE_BUSINESS", "price_business_placeholder"),
        "limits": {
            "tenders": -1,
            "ai_analysis": True,
            "team_members": -1,
            "api_access": True,
        },
        "features": [
            "Nielimitowane przetargi",
            "Pełne AI analizy",
            "Dostęp API",
            "Nieograniczony zespół",
            "Priorytetowe wsparcie",
            "Zaawansowane raporty",
        ],
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_pln": None,
        "price_label": "Wycena indywidualna",
        "billing": "roczny",
        "stripe_price_id": None,
        "limits": {
            "tenders": -1,
            "ai_analysis": True,
            "team_members": -1,
            "api_access": True,
        },
        "features": [
            "On-premise / self-hosted",
            "SSO / SAML",
            "SLA 99.9%",
            "Dedykowany opiekun",
            "Własne integracje",
            "Audyt bezpieczeństwa",
        ],
    },
]

# price_id → plan name mapping (used in webhook handlers)
PRICE_ID_TO_PLAN: dict[str, str] = {
    p["stripe_price_id"]: p["id"]
    for p in PLANS
    if p.get("stripe_price_id")
}


# ─── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan_id: str = "pro"
    success_url: str = "/billing/success"
    cancel_url: str = "/pricing"


# ─── Internal helpers ──────────────────────────────────────────────────────────

def _get_or_create_subscription(db: Any, org_id: str) -> dict[str, Any]:
    """Fetch subscription row for org; create a free one if missing."""
    row = db.execute(
        text("SELECT * FROM subscription WHERE org_id = :oid"),
        {"oid": org_id},
    ).fetchone()
    if not row:
        db.execute(
            text(
                """
                INSERT INTO subscription (org_id, plan, status)
                VALUES (:oid, 'free', 'active')
                ON CONFLICT (org_id) DO NOTHING
                """
            ),
            {"oid": org_id},
        )
        db.commit()
        row = db.execute(
            text("SELECT * FROM subscription WHERE org_id = :oid"),
            {"oid": org_id},
        ).fetchone()
    return dict(row._mapping) if row else {}


def _resolve_org_id_from_customer(db: Any, customer_id: str) -> str | None:
    """Resolve org_id by stripe_customer_id (from subscription or organizations table)."""
    row = db.execute(
        text("SELECT org_id FROM subscription WHERE stripe_customer_id = :cid"),
        {"cid": customer_id},
    ).fetchone()
    if row:
        return str(row.org_id)
    # Also check organizations table (set during checkout)
    row2 = db.execute(
        text("SELECT id FROM organizations WHERE stripe_customer_id = :cid"),
        {"cid": customer_id},
    ).fetchone()
    return str(row2.id) if row2 else None


def _ts(unix: int | None) -> datetime | None:
    """Convert Unix timestamp to UTC datetime."""
    if unix is None:
        return None
    return datetime.fromtimestamp(unix, tz=timezone.utc)


def _plan_from_price(price_id: str | None) -> str:
    """Map Stripe price_id to internal plan name."""
    if not price_id:
        return "free"
    return PRICE_ID_TO_PLAN.get(price_id, "pro")


# ─── Webhook event handlers ────────────────────────────────────────────────────

async def handle_checkout_completed(obj: dict[str, Any], db: Any) -> None:
    """checkout.session.completed — activate paid plan, persist stripe IDs."""
    session_mode = obj.get("mode", "")
    if session_mode != "subscription":
        logger.info("Ignoring non-subscription checkout: %s", session_mode)
        return

    customer_id = obj.get("customer", "")
    subscription_id = obj.get("subscription", "")
    org_id: str | None = None

    # Try metadata first (set during Session.create)
    meta = obj.get("metadata", {})
    org_id = meta.get("org_id") or None

    if not org_id:
        org_id = _resolve_org_id_from_customer(db, customer_id)

    if not org_id:
        logger.exception(
            "checkout.session.completed: cannot resolve org_id for customer=%s", customer_id, exc_info=True
        )
        return

    # Determine plan from line items price (best effort)
    line_items = obj.get("line_items", {}).get("data", [])
    price_id = line_items[0]["price"]["id"] if line_items else None

    # Persist stripe_customer_id on organizations table
    db.execute(
        text(
            """
            UPDATE organizations
            SET stripe_customer_id     = :cid,
                stripe_subscription_id = :sid,
                plan                   = :plan
            WHERE id = :oid
            """
        ),
        {
            "cid": customer_id,
            "sid": subscription_id,
            "plan": _plan_from_price(price_id),
            "oid": org_id,
        },
    )

    # Upsert subscription row
    db.execute(
        text(
            """
            INSERT INTO subscription
                (org_id, plan, status, stripe_customer_id, stripe_subscription_id,
                 stripe_price_id, updated_at)
            VALUES
                (:oid, :plan, 'active', :cid, :sid, :price_id, now())
            ON CONFLICT (org_id) DO UPDATE SET
                plan                   = EXCLUDED.plan,
                status                 = 'active',
                stripe_customer_id     = EXCLUDED.stripe_customer_id,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                stripe_price_id        = EXCLUDED.stripe_price_id,
                payment_failed         = FALSE,
                cancel_at_period_end   = FALSE,
                updated_at             = now()
            """
        ),
        {
            "oid": org_id,
            "plan": _plan_from_price(price_id),
            "cid": customer_id,
            "sid": subscription_id,
            "price_id": price_id,
        },
    )
    db.commit()
    logger.info(
        "checkout.completed: org=%s plan=%s customer=%s sub=%s",
        org_id, _plan_from_price(price_id), customer_id, subscription_id,
    )


async def handle_subscription_updated(obj: dict[str, Any], db: Any) -> None:
    """customer.subscription.updated — sync plan, status, trial/period dates."""
    customer_id = obj.get("customer", "")
    sub_id = obj.get("id", "")
    status = obj.get("status", "active")
    cancel_at_period_end = obj.get("cancel_at_period_end", False)

    # Stripe status mapping
    internal_status = {
        "active": "active",
        "trialing": "trialing",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "past_due",
        "incomplete_expired": "canceled",
        "paused": "past_due",
    }.get(status, status)

    # Resolve price/plan from items
    items = obj.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else None
    plan = _plan_from_price(price_id)

    period_start = _ts(obj.get("current_period_start"))
    period_end = _ts(obj.get("current_period_end"))
    trial_end = _ts(obj.get("trial_end"))

    org_id = _resolve_org_id_from_customer(db, customer_id)
    if not org_id:
        logger.exception("subscription.updated: unknown customer=%s", exc_info=True)
        return

    db.execute(
        text(
            """
            INSERT INTO subscription
                (org_id, plan, status, stripe_customer_id, stripe_subscription_id,
                 stripe_price_id, current_period_start, current_period_end,
                 trial_end, cancel_at_period_end, updated_at)
            VALUES
                (:oid, :plan, :status, :cid, :sid, :price_id,
                 :ps, :pe, :te, :cape, now())
            ON CONFLICT (org_id) DO UPDATE SET
                plan                   = EXCLUDED.plan,
                status                 = EXCLUDED.status,
                stripe_customer_id     = EXCLUDED.stripe_customer_id,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                stripe_price_id        = EXCLUDED.stripe_price_id,
                current_period_start   = EXCLUDED.current_period_start,
                current_period_end     = EXCLUDED.current_period_end,
                trial_end              = EXCLUDED.trial_end,
                cancel_at_period_end   = EXCLUDED.cancel_at_period_end,
                updated_at             = now()
            """
        ),
        {
            "oid": org_id, "plan": plan, "status": internal_status,
            "cid": customer_id, "sid": sub_id, "price_id": price_id,
            "ps": period_start, "pe": period_end, "te": trial_end,
            "cape": cancel_at_period_end,
        },
    )
    # Keep organizations.plan in sync
    db.execute(
        text("UPDATE organizations SET plan = :plan WHERE id = :oid"),
        {"plan": plan, "oid": org_id},
    )
    db.commit()
    logger.info(
        "subscription.updated: org=%s plan=%s status=%s cancel_at_end=%s",
        org_id, plan, internal_status, cancel_at_period_end,
    )


async def handle_subscription_deleted(obj: dict[str, Any], db: Any) -> None:
    """customer.subscription.deleted — 3-day grace period, then downgrade to free."""
    customer_id = obj.get("customer", "")
    org_id = _resolve_org_id_from_customer(db, customer_id)
    if not org_id:
        logger.exception("subscription.deleted: unknown customer=%s", exc_info=True)
        return

    grace_until = datetime.now(tz=timezone.utc) + timedelta(days=3)

    db.execute(
        text(
            """
            UPDATE subscription
            SET status          = 'canceled',
                cancel_at_period_end = TRUE,
                grace_until     = :grace,
                updated_at      = now()
            WHERE org_id = :oid
            """
        ),
        {"grace": grace_until, "oid": org_id},
    )
    # Schedule plan downgrade: mark organizations as 'free' only after grace period.
    # For immediate consistency we leave organizations.plan as-is and let a cron/
    # background task detect grace_until < now().  However, if there is no background
    # task, we downgrade immediately after the grace window (conservative approach):
    # here we just log the intent and leave the plan alone during grace.
    logger.info(
        "subscription.deleted: org=%s grace_until=%s — will downgrade to free after grace",
        org_id, grace_until.isoformat(),
    )
    db.commit()


async def handle_payment_succeeded(obj: dict[str, Any], db: Any) -> None:
    """invoice.payment_succeeded — clear payment_failed flag, extend period."""
    customer_id = obj.get("customer", "")
    period_end_unix = obj.get("lines", {}).get("data", [{}])[0].get(
        "period", {}
    ).get("end") or obj.get("period_end")
    period_end = _ts(period_end_unix)

    org_id = _resolve_org_id_from_customer(db, customer_id)
    if not org_id:
        logger.exception("invoice.payment_succeeded: unknown customer=%s", exc_info=True)
        return

    db.execute(
        text(
            """
            UPDATE subscription
            SET payment_failed       = FALSE,
                status               = CASE WHEN status = 'past_due' THEN 'active' ELSE status END,
                current_period_end   = COALESCE(:pe, current_period_end),
                updated_at           = now()
            WHERE org_id = :oid
            """
        ),
        {"pe": period_end, "oid": org_id},
    )
    db.commit()
    logger.info("invoice.payment_succeeded: org=%s period_end=%s", org_id, period_end)


async def handle_payment_failed(obj: dict[str, Any], db: Any) -> None:
    """invoice.payment_failed — flag payment failure, mock-send notification email."""
    customer_id = obj.get("customer", "")
    attempt = obj.get("attempt_count", 1)
    amount = obj.get("amount_due", 0)

    org_id = _resolve_org_id_from_customer(db, customer_id)
    if not org_id:
        logger.exception("invoice.payment_failed: unknown customer=%s", exc_info=True)
        return

    db.execute(
        text(
            """
            UPDATE subscription
            SET payment_failed = TRUE,
                status         = 'past_due',
                updated_at     = now()
            WHERE org_id = :oid
            """
        ),
        {"oid": org_id},
    )
    # Also reflect on organizations table
    db.execute(
        text("UPDATE organizations SET plan = plan WHERE id = :oid"),
        {"oid": org_id},
    )
    db.commit()

    # Mock email: log only (replace with real smtp/sendgrid in production)
    logger.warning(
        "[MOCK EMAIL] invoice.payment_failed: org=%s customer=%s amount=%s attempt=%s "
        "→ would send 'Payment failed' email to org admins",
        org_id, customer_id, amount, attempt,
    )


# ─── Webhook signature verification ───────────────────────────────────────────

def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """
    Verify Stripe webhook signature using timestamp + HMAC-SHA256.
    Stripe sig header format: t=<ts>,v1=<sig>[,v0=<old_sig>]
    See: https://stripe.com/docs/webhooks/signatures
    """
    try:
        parts = dict(kv.split("=", 1) for kv in sig_header.split(",") if "=" in kv)
        timestamp = parts.get("t", "")
        v1 = parts.get("v1", "")
        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)
    except Exception as exc:
        logger.debug("Stripe signature verification error: %s", exc)
        return False


# ─── Routes ────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans() -> list[dict[str, Any]]:
    """Return all available subscription plans (public)."""
    return PLANS


@router.post("/checkout")
def checkout(body: CheckoutRequest, current_user: AuthUser) -> dict[str, str]:
    """Create Stripe Checkout session. Falls back to placeholder if Stripe not configured."""
    plan = next((p for p in PLANS if p["id"] == body.plan_id), None)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Nieznany plan: {body.plan_id}")

    if plan["id"] in ("free", "enterprise"):
        return {
            "redirect_url": "/contact",
            "message": "Skontaktuj się z nami dla tego planu",
            "plan_id": body.plan_id,
        }

    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_price_id = plan.get("stripe_price_id", "")

    if stripe_key and stripe_key.startswith("sk_") and stripe_price_id and not stripe_price_id.endswith("_placeholder"):
        try:
            import stripe  # type: ignore
            stripe.api_key = stripe_key
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": stripe_price_id, "quantity": 1}],
                success_url=body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=body.cancel_url,
                metadata={
                    "org_id": current_user.org_id or "",
                    "user_id": current_user.user_id,
                },
            )
            return {
                "redirect_url": session.url,
                "session_id": session.id,
                "plan_id": body.plan_id,
            }
        except Exception as e:
            logger.exception("Stripe checkout error: %s", exc_info=True)

    return {
        "redirect_url": "#stripe-not-configured",
        "message": "Stripe nie jest jeszcze skonfigurowany. Skontaktuj się z support@terra.os",
        "plan_id": body.plan_id,
    }


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: DB,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
) -> dict[str, Any]:
    """Handle Stripe webhooks (full subscription lifecycle)."""
    payload = await request.body()

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if webhook_secret:
        sig = stripe_signature or ""
        # Try official stripe SDK first
        if sig:
            try:
                import stripe  # type: ignore
                stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
                stripe.Webhook.construct_event(payload, sig, webhook_secret)
            except Exception:
                # Fallback to manual HMAC verification
                if not _verify_stripe_signature(payload, sig, webhook_secret):
                    logger.warning("Invalid Stripe webhook signature — rejecting")
                    raise HTTPException(status_code=400, detail="Invalid webhook signature")
        else:
            logger.warning("Webhook received without stripe-signature header (secret configured)")
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    # If no STRIPE_WEBHOOK_SECRET configured → test/mock mode, accept all

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})

    handlers = {
        "checkout.session.completed":   handle_checkout_completed,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_deleted,
        "invoice.payment_succeeded":     handle_payment_succeeded,
        "invoice.payment_failed":        handle_payment_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            await handler(data_obj, db)
        except Exception as exc:
            logger.exception("Webhook handler error for event %s: %s", event_type, exc)
            # Always return 200 to Stripe to avoid retries for handled events
            return {"received": True, "error": str(exc)}
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"received": True, "event_type": event_type}


@router.get("/subscription")
def get_subscription(current_user: AuthUser, db: DB) -> dict[str, Any]:
    """Return current subscription plan and full status for user's organization."""
    if not current_user.org_id:
        return {"plan": "free", "status": "active", "org_id": None, "plan_details": PLANS[0]}

    sub = _get_or_create_subscription(db, current_user.org_id)

    # If grace period expired, downgrade to free automatically
    grace_until = sub.get("grace_until")
    if grace_until and datetime.now(tz=timezone.utc) > grace_until:
        db.execute(
            text(
                """
                UPDATE subscription
                SET plan       = 'free',
                    status     = 'active',
                    grace_until = NULL,
                    updated_at  = now()
                WHERE org_id = :oid
                """
            ),
            {"oid": current_user.org_id},
        )
        db.execute(
            text("UPDATE organizations SET plan = 'free' WHERE id = :oid"),
            {"oid": current_user.org_id},
        )
        db.commit()
        sub["plan"] = "free"
        sub["status"] = "active"
        sub["grace_until"] = None

    plan_id = sub.get("plan", "free")
    plan_details = next((p for p in PLANS if p["id"] == plan_id), PLANS[0])

    return {
        "plan": plan_id,
        "status": sub.get("status", "active"),
        "org_id": current_user.org_id,
        "stripe_customer_id": sub.get("stripe_customer_id"),
        "stripe_subscription_id": sub.get("stripe_subscription_id"),
        "current_period_start": sub.get("current_period_start"),
        "current_period_end": sub.get("current_period_end"),
        "trial_end": sub.get("trial_end"),
        "payment_failed": sub.get("payment_failed", False),
        "cancel_at_period_end": sub.get("cancel_at_period_end", False),
        "grace_until": sub.get("grace_until"),
        "plan_details": plan_details,
    }


@router.post("/cancel")
def cancel_subscription(current_user: AuthUser, db: DB) -> dict[str, Any]:
    """Cancel subscription at period end. Uses Stripe API if configured, otherwise sets flag."""
    if not current_user.org_id:
        raise HTTPException(status_code=400, detail="Brak organizacji")

    sub = _get_or_create_subscription(db, current_user.org_id)
    if sub.get("plan", "free") == "free":
        raise HTTPException(status_code=400, detail="Plan Free nie wymaga anulowania")

    stripe_sub_id = sub.get("stripe_subscription_id")
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")

    if stripe_key and stripe_key.startswith("sk_") and stripe_sub_id:
        try:
            import stripe  # type: ignore
            stripe.api_key = stripe_key
            stripe.Subscription.modify(stripe_sub_id, cancel_at_period_end=True)
            logger.info("Stripe subscription cancel_at_period_end=True for sub=%s", stripe_sub_id)
        except Exception as e:
            logger.exception("Stripe cancel error: %s", exc_info=True)
            # Fallback: set flag locally
            db.execute(
                text(
                    "UPDATE subscription SET cancel_at_period_end = TRUE, updated_at = now() "
                    "WHERE org_id = :oid"
                ),
                {"oid": current_user.org_id},
            )
            db.commit()
    else:
        # Mock / no Stripe: set flag locally
        db.execute(
            text(
                "UPDATE subscription SET cancel_at_period_end = TRUE, updated_at = now() "
                "WHERE org_id = :oid"
            ),
            {"oid": current_user.org_id},
        )
        db.commit()
        logger.info(
            "Subscription cancel_at_period_end=TRUE set locally for org=%s (Stripe not configured)",
            current_user.org_id,
        )

    return {
        "message": "Subskrypcja zostanie anulowana na koniec okresu rozliczeniowego.",
        "cancel_at_period_end": True,
        "org_id": current_user.org_id,
    }


# S107 — GET /api/v2/billing/checkout-url?plan=pro
@router.get("/checkout-url")
def get_checkout_url(plan: str = "pro") -> dict[str, Any]:
    """S107 — Zwróć URL do Stripe Checkout (lub placeholder)."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if stripe_key and stripe_key.startswith("sk_"):
        try:
            import stripe  # type: ignore
            stripe.api_key = stripe_key
            plan_prices = {"pro": "price_pro_placeholder", "starter": "price_starter_placeholder", "enterprise": "price_enterprise_placeholder"}
            price_id = plan_prices.get(plan)
            if not price_id:
                raise HTTPException(status_code=400, detail=f"Nieznany plan: {plan}")
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url="https://app.terra.os/billing?success=1",
                cancel_url="https://app.terra.os/billing?cancel=1",
            )
            return {"url": session.url, "plan": plan}
        except Exception:
            pass
    return {"url": "https://stripe.com/pay/placeholder", "plan": plan}
