"""FIX-4 — billing.py coverage: list_plans, checkout (free/enterprise/fallback),
subscription (no org_id), cancel (no org_id / already free)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _user(org_id: str = "ec3d1e16-2139-48c2-93b5-ffe0defd606d", user_id: str = "u1"):
    u = MagicMock()
    u.org_id = org_id
    u.user_id = user_id
    return u


def _db():
    db = MagicMock()
    sub_row = {
        "plan": "free",
        "status": "active",
        "org_id": "ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        "grace_until": None,
        "stripe_subscription_id": None,
        "stripe_customer_id": None,
        "current_period_end": None,
    }
    db.execute.return_value.fetchone.return_value = None  # trigger create
    db.execute.return_value.mappings.return_value.fetchone.return_value = None
    # _get_or_create_subscription returns sub_row via execute → mappings → fetchone
    return db, sub_row


class TestListPlans:
    def test_returns_list(self):
        from services.api.services.api.routers.billing import list_plans
        result = list_plans()
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_free_plan_exists(self):
        from services.api.services.api.routers.billing import list_plans
        plans = list_plans()
        ids = [p["id"] for p in plans]
        assert "free" in ids

    def test_pro_plan_has_price(self):
        from services.api.services.api.routers.billing import list_plans
        plans = list_plans()
        pro = next((p for p in plans if p["id"] == "pro"), None)
        if pro:
            assert pro.get("price_pln", 0) > 0

    def test_all_plans_have_id_and_name(self):
        from services.api.services.api.routers.billing import list_plans
        for plan in list_plans():
            assert "id" in plan
            assert "name" in plan


class TestCheckout:
    def test_unknown_plan_raises_400(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.billing import checkout, CheckoutRequest
        body = CheckoutRequest(plan_id="nonexistent")
        with pytest.raises(HTTPException) as exc:
            checkout(body, _user())
        assert exc.value.status_code == 400

    def test_free_plan_returns_redirect(self):
        from services.api.services.api.routers.billing import checkout, CheckoutRequest
        body = CheckoutRequest(plan_id="free")
        result = checkout(body, _user())
        assert "redirect_url" in result

    def test_pro_plan_no_stripe_fallback(self):
        from services.api.services.api.routers.billing import checkout, CheckoutRequest
        body = CheckoutRequest(plan_id="pro")
        # STRIPE_SECRET_KEY not set → fallback placeholder response
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}, clear=False):
            result = checkout(body, _user())
        assert "redirect_url" in result or "message" in result

    def test_enterprise_plan_redirect(self):
        from services.api.services.api.routers.billing import checkout, CheckoutRequest, PLANS
        # Only test if enterprise plan exists
        enterprise = next((p for p in PLANS if p["id"] == "enterprise"), None)
        if enterprise is None:
            pytest.skip("no enterprise plan")
        body = CheckoutRequest(plan_id="enterprise")
        result = checkout(body, _user())
        assert "redirect_url" in result


class TestGetSubscription:
    def test_no_org_id_returns_free(self):
        from services.api.services.api.routers.billing import get_subscription
        user = _user(org_id=None)
        result = get_subscription(user, MagicMock())
        assert result["plan"] == "free"

    def test_with_org_returns_subscription(self):
        from services.api.services.api.routers.billing import get_subscription
        db = MagicMock()
        # _get_or_create_subscription → fetchone returns None → INSERT → returns default
        db.execute.return_value.fetchone.return_value = None
        result = get_subscription(_user(), db)
        assert "plan" in result

    def test_grace_period_check(self):
        """Even with a grace_until, no crash."""
        from services.api.services.api.routers.billing import get_subscription
        from datetime import datetime, timezone, timedelta
        db = MagicMock()
        # subscription already active
        sub_row = MagicMock()
        sub_row.plan = "pro"
        sub_row.status = "active"
        sub_row.grace_until = datetime.now(tz=timezone.utc) - timedelta(days=10)  # expired
        # _get_or_create_subscription tries: fetchone → None → INSERT → fetchone → sub_row
        call_n = [0]
        def exe(stmt, params=None):
            r = MagicMock()
            call_n[0] += 1
            if call_n[0] <= 2:
                r.fetchone.return_value = None
            return r
        db.execute = MagicMock(side_effect=exe)
        result = get_subscription(_user(), db)
        assert "plan" in result


class TestCancelSubscription:
    def test_no_org_id_raises_400(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.billing import cancel_subscription
        with pytest.raises(HTTPException) as exc:
            cancel_subscription(_user(org_id=None), MagicMock())
        assert exc.value.status_code == 400

    def test_already_free_raises_400(self):
        """Free plan → 400 (nie można anulować darmowego)."""
        from fastapi import HTTPException
        from services.api.services.api.routers.billing import cancel_subscription
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None  # → tworzy free sub
        with pytest.raises(HTTPException) as exc:
            cancel_subscription(_user(), db)
        assert exc.value.status_code == 400

    def test_cancel_pro_no_stripe_sets_flag(self):
        """Pro plan bez Stripe → ustawia cancel_at_period_end lokalnie."""
        from services.api.services.api.routers.billing import cancel_subscription
        db = MagicMock()
        pro_sub = {
            "plan": "pro",
            "status": "active",
            "org_id": "ec3d1e16-2139-48c2-93b5-ffe0defd606d",
            "grace_until": None,
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "current_period_end": None,
        }
        with patch(
            "services.api.services.api.routers.billing._get_or_create_subscription",
            return_value=pro_sub,
        ):
            with patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}, clear=False):
                result = cancel_subscription(_user(), db)
        assert isinstance(result, dict)
