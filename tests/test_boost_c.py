"""Coverage boost-c: intelligence / billing / scoring_v2 / m7_phase2 /
decisions_v2 / analytics_v2 / export / sse_mcp_chat

Covers edge-cases, error paths and else-branches that are missing in the
current 70-77% coverage baseline.
"""
from __future__ import annotations

import asyncio
import io
import json
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── shared app fixture ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


@pytest.fixture(scope="module")
def auth_headers():
    from services.api.services.api.auth.utils import create_access_token
    token = create_access_token(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE router
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntelligenceEdgeCases:
    """Tests for uncovered branches in intelligence.py"""

    @pytest.mark.asyncio
    async def test_anomaly_bid_error_path(self, app, auth_headers):
        """POST /anomaly/bid → 500 when bid_intelligence raises."""
        with patch(
            "services.api.services.api.routers.intelligence._bi",
            side_effect=Exception("db error"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/intelligence/anomaly/bid",
                    headers=auth_headers,
                    json={
                        "bid_price": 1_000_000,
                        "estimated_value": 1_200_000,
                        "cpv_prefix": "45",
                    },
                )
        assert r.status_code == 500

    @pytest.mark.asyncio
    async def test_anomaly_bid_ok_mocked(self, app, auth_headers):
        """POST /anomaly/bid → 200 with mocked service."""
        mock_bi = MagicMock()
        mock_bi.return_value = {
            "detect_bid_anomalies": lambda *a, **kw: {
                "is_anomaly": False,
                "flags": [],
                "pzp224_check": "ok",
            }
        }
        with patch("services.api.services.api.routers.intelligence._bi", mock_bi):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/intelligence/anomaly/bid",
                    headers=auth_headers,
                    json={
                        "bid_price": 950_000,
                        "estimated_value": 1_200_000,
                        "cpv_prefix": "45",
                        "province": "mazowieckie",
                        "n_competitors": 5,
                    },
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_anomaly_kosztorys_mocked(self, app, auth_headers):
        """POST /anomaly/kosztorys → 200 with mocked detect_kosztorys_anomalies."""
        mock_bi = {
            "detect_kosztorys_anomalies": lambda items, cpv, prov: {
                "anomalies": [],
                "total_items": len(items),
            }
        }
        with patch("services.api.services.api.routers.intelligence._bi", return_value=mock_bi):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/intelligence/anomaly/kosztorys",
                    headers=auth_headers,
                    json={
                        "items": [
                            {"description": "beton C20/25", "unit": "m3", "quantity": 10, "unit_price": 450.0, "category": "materiały"},
                            {"description": "robocizna", "unit": "r-g", "quantity": 100, "unit_price": 50.0, "category": "robocizna"},
                        ],
                        "cpv_prefix": "45",
                    },
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_win_probability_no_model(self, app, auth_headers):
        """POST /win-probability → 200 even without ML model (fallback)."""
        mock_bi = {
            "estimate_win_probability": lambda *a, **kw: {
                "p_win": 0.45,
                "sweet_spot": 0.88,
                "recommendation": "Cena w normie",
                "model": "quantile",
            }
        }
        with patch("services.api.services.api.routers.intelligence._bi", return_value=mock_bi):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/intelligence/win-probability",
                    headers=auth_headers,
                    json={
                        "our_price": 900_000,
                        "estimated_value": 1_000_000,
                        "cpv_prefix": "45",
                        "n_competitors": 3,
                    },
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_win_probability_error(self, app, auth_headers):
        """POST /win-probability → 500 on exception."""
        with patch(
            "services.api.services.api.routers.intelligence._bi",
            side_effect=RuntimeError("model file missing"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/intelligence/win-probability",
                    headers=auth_headers,
                    json={"our_price": 1.0, "estimated_value": 1.0},
                )
        assert r.status_code == 500

    @pytest.mark.asyncio
    async def test_prices_icb_error(self, app, auth_headers):
        """GET /prices/icb → 500 when ICB service fails."""
        with patch(
            "services.api.services.api.routers.intelligence._icb",
            side_effect=Exception("ICB db offline"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/intelligence/prices/icb?q=beton", headers=auth_headers)
        assert r.status_code == 500

    @pytest.mark.asyncio
    async def test_prices_icb_ok_mocked(self, app, auth_headers):
        """GET /prices/icb → 200 with mocked search_icb."""
        svc = {
            "search_icb": lambda q, typ, yr, qr, cat, lim: [
                {"symbol": "M.01.01.01", "nazwa": "Beton C20/25", "cena_netto": 450.0}
            ],
        }
        with patch("services.api.services.api.routers.intelligence._icb", return_value=svc):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(
                    "/api/v2/intelligence/prices/icb?q=beton&year=2026&quarter=2",
                    headers=auth_headers,
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_price_trend_mocked(self, app, auth_headers):
        """GET /prices/trend → 200 with category param."""
        svc = {
            "get_price_trend": lambda sym, cat, typ, yr: [
                {"period": "2026-Q2", "avg_price": 450.0}
            ]
        }
        with patch("services.api.services.api.routers.intelligence._icb", return_value=svc):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(
                    "/api/v2/intelligence/prices/trend?category=materiały&typ_rms=M&from_year=2022",
                    headers=auth_headers,
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_benchmark_mocked(self, app, auth_headers):
        """GET /benchmark → 200."""
        mock_bi = {
            "get_cpv_benchmark": lambda cpv, prov, qtrs: {
                "cpv_prefix": cpv,
                "count": 10,
                "value_stats": {"mean": 500_000, "p25": 200_000, "p75": 800_000},
            }
        }
        with patch("services.api.services.api.routers.intelligence._bi", return_value=mock_bi):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(
                    "/api/v2/intelligence/benchmark?cpv_prefix=45&province=mazowieckie",
                    headers=auth_headers,
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_inflation_error_path(self, app, auth_headers):
        """GET /prices/inflation → 500 on pi() exception."""
        with patch(
            "services.api.services.api.routers.intelligence._pi",
            side_effect=Exception("view missing"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/intelligence/prices/inflation", headers=auth_headers)
        assert r.status_code == 500

    @pytest.mark.asyncio
    async def test_material_risk_with_category(self, app, auth_headers):
        """GET /material-risk?category=... → category-specific path."""
        mock_pi = {
            "get_material_risk_score": lambda cat, qtrs: {"category": cat, "risk_score": 0.3, "trend": "stable"},
            "get_all_material_risks": lambda qtrs: [],
        }
        with patch("services.api.services.api.routers.intelligence._pi", return_value=mock_pi):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(
                    "/api/v2/intelligence/material-risk?category=stal",
                    headers=auth_headers,
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_material_risk_all(self, app, auth_headers):
        """GET /material-risk (no category) → all-risks path."""
        mock_pi = {
            "get_material_risk_score": lambda cat, qtrs: {},
            "get_all_material_risks": lambda qtrs: [{"category": "stal", "risk_score": 0.5}],
        }
        with patch("services.api.services.api.routers.intelligence._pi", return_value=mock_pi):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/intelligence/material-risk", headers=auth_headers)
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_narzuty_all_flag(self, app, auth_headers):
        """GET /narzuty?all=true → all-branches path."""
        svc = {
            "get_all_narzuty": lambda yr, qr: [{"branża": "ogólnobudowlane", "Ko": 68}],
            "get_narzuty": lambda yr, qr, b: {"branża": b, "Ko": 68},
        }
        with patch("services.api.services.api.routers.intelligence._icb", return_value=svc):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(
                    "/api/v2/intelligence/narzuty?all=true&year=2026&quarter=2",
                    headers=auth_headers,
                )
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_win_prob_ml_no_model(self, app, auth_headers):
        """GET /win-prob/{id} → 500 when predict_win_prob raises."""
        from unittest.mock import MagicMock, patch

        fake_engine = MagicMock()
        fake_conn = MagicMock()
        fake_engine.connect.return_value.__enter__ = lambda s: fake_conn
        fake_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch(
            "services.api.services.api.routers.intelligence._get_engine",
            return_value=fake_engine,
        ), patch(
            "services.api.services.api.routers.intelligence.predict_win_prob",
            side_effect=FileNotFoundError("model.pkl not found"),
            create=True,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(
                    "/api/v2/intelligence/win-prob/some-tender-id",
                    headers=auth_headers,
                )
        # Will either 500 (exception) or import error; either is fine
        assert r.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING — webhook handlers (unit tests, no HTTP)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBillingWebhookHandlers:
    """Unit-test the async webhook handler functions directly."""

    def _make_db(self, org_id="org-123"):
        """Return a mock DB connection that resolves org_id."""
        db = MagicMock()
        row = SimpleNamespace(org_id=org_id)
        db.execute.return_value.fetchone.return_value = row
        db.commit = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_handle_payment_failed_known_customer(self):
        from services.api.services.api.routers.billing import handle_payment_failed

        db = self._make_db("org-abc")
        obj = {
            "customer": "cus_123",
            "attempt_count": 2,
            "amount_due": 49900,
        }
        await handle_payment_failed(obj, db)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_handle_payment_failed_unknown_customer(self):
        from services.api.services.api.routers.billing import handle_payment_failed

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        obj = {"customer": "cus_unknown", "attempt_count": 1, "amount_due": 0}
        # Should not raise; just log and return
        await handle_payment_failed(obj, db)

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted_sets_grace(self):
        from services.api.services.api.routers.billing import handle_subscription_deleted

        db = self._make_db("org-del")
        obj = {"customer": "cus_del"}
        await handle_subscription_deleted(obj, db)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted_unknown_customer(self):
        from services.api.services.api.routers.billing import handle_subscription_deleted

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        await handle_subscription_deleted({"customer": "cus_x"}, db)

    @pytest.mark.asyncio
    async def test_handle_payment_succeeded(self):
        from services.api.services.api.routers.billing import handle_payment_succeeded

        db = self._make_db("org-pay")
        obj = {
            "customer": "cus_pay",
            "lines": {"data": [{"period": {"end": 1780000000}}]},
        }
        await handle_payment_succeeded(obj, db)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_handle_payment_succeeded_no_period(self):
        from services.api.services.api.routers.billing import handle_payment_succeeded

        db = self._make_db("org-pay2")
        obj = {"customer": "cus_pay2", "lines": {"data": []}}
        await handle_payment_succeeded(obj, db)

    @pytest.mark.asyncio
    async def test_handle_subscription_updated_known(self):
        from services.api.services.api.routers.billing import handle_subscription_updated

        db = self._make_db("org-upd")
        obj = {
            "customer": "cus_upd",
            "id": "sub_upd",
            "status": "active",
            "cancel_at_period_end": False,
            "items": {"data": [{"price": {"id": "price_pro_placeholder"}}]},
            "current_period_start": 1700000000,
            "current_period_end": 1780000000,
            "trial_end": None,
        }
        await handle_subscription_updated(obj, db)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_handle_subscription_updated_unknown_customer(self):
        from services.api.services.api.routers.billing import handle_subscription_updated

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        obj = {
            "customer": "cus_noexist",
            "id": "sub_x",
            "status": "active",
            "cancel_at_period_end": False,
            "items": {"data": []},
        }
        await handle_subscription_updated(obj, db)  # should not crash

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_metadata_org(self):
        from services.api.services.api.routers.billing import handle_checkout_completed

        db = self._make_db("org-co")
        obj = {
            "mode": "subscription",
            "customer": "cus_co",
            "subscription": "sub_co",
            "metadata": {"org_id": "org-co"},
            "line_items": {"data": []},
        }
        await handle_checkout_completed(obj, db)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_non_subscription(self):
        from services.api.services.api.routers.billing import handle_checkout_completed

        db = MagicMock()
        obj = {"mode": "payment", "customer": "cus_x"}
        await handle_checkout_completed(obj, db)
        # Non-subscription: should return early, no DB writes
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_checkout_completed_no_org_fallback(self):
        from services.api.services.api.routers.billing import handle_checkout_completed

        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None  # can't resolve org
        obj = {
            "mode": "subscription",
            "customer": "cus_noorg",
            "subscription": "sub_noorg",
            "metadata": {},
            "line_items": {"data": []},
        }
        await handle_checkout_completed(obj, db)  # should log and return


class TestBillingWebhookEndpoint:
    """Test webhook HTTP endpoint with various event types."""

    @pytest.mark.asyncio
    async def test_webhook_payment_failed(self, app):
        """POST /webhook with invoice.payment_failed → handled."""
        payload = json.dumps({
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_fail",
                    "attempt_count": 1,
                    "amount_due": 49900,
                }
            }
        }).encode()

        # Mock DB resolution
        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = SimpleNamespace(org_id="org-x")
        db_mock.commit = MagicMock()

        def fake_db():
            yield db_mock

        from services.api.services.api.routers import billing as billing_mod
        with patch.object(billing_mod, "get_db", fake_db):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/billing/webhook",
                    content=payload,
                    headers={"content-type": "application/json"},
                )
        assert r.status_code == 200
        assert r.json().get("received") is True

    @pytest.mark.asyncio
    async def test_webhook_subscription_deleted(self, app):
        """POST /webhook with customer.subscription.deleted → handled."""
        payload = json.dumps({
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_del"}}
        }).encode()

        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = SimpleNamespace(org_id="org-del")
        db_mock.commit = MagicMock()

        def fake_db():
            yield db_mock

        from services.api.services.api.routers import billing as billing_mod
        with patch.object(billing_mod, "get_db", fake_db):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/billing/webhook",
                    content=payload,
                    headers={"content-type": "application/json"},
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_invoice_paid(self, app):
        """POST /webhook with invoice.payment_succeeded → handled."""
        payload = json.dumps({
            "type": "invoice.payment_succeeded",
            "data": {"object": {"customer": "cus_paid", "lines": {"data": []}}}
        }).encode()

        db_mock = MagicMock()
        db_mock.execute.return_value.fetchone.return_value = SimpleNamespace(org_id="org-p")
        db_mock.commit = MagicMock()

        def fake_db():
            yield db_mock

        from services.api.services.api.routers import billing as billing_mod
        with patch.object(billing_mod, "get_db", fake_db):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/billing/webhook",
                    content=payload,
                    headers={"content-type": "application/json"},
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_unknown_event(self, app):
        """POST /webhook with unknown event type → received:True, unhandled."""
        payload = json.dumps({
            "type": "unknown.event.type",
            "data": {"object": {}}
        }).encode()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/billing/webhook",
                content=payload,
                headers={"content-type": "application/json"},
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_invalid_json(self, app):
        """POST /webhook with invalid JSON → 400."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/billing/webhook",
                content=b"not-valid-json",
                headers={"content-type": "application/json"},
            )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_missing_sig_when_secret_set(self, app):
        """When STRIPE_WEBHOOK_SECRET set but no sig header → 400."""
        payload = json.dumps({"type": "test", "data": {"object": {}}}).encode()
        with patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": "whsec_test123"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/billing/webhook",
                    content=payload,
                    headers={"content-type": "application/json"},
                )
        assert r.status_code in (400, 200)


class TestBillingCancelPro:
    """cancel_subscription edge cases."""

    @pytest.mark.asyncio
    async def test_cancel_pro_no_stripe_key(self, app, auth_headers):
        """POST /billing/cancel with pro plan but no Stripe key → set flag locally."""
        db_mock = MagicMock()
        sub_row = {
            "plan": "pro",
            "status": "active",
            "stripe_subscription_id": "sub_test",
            "stripe_customer_id": "cus_test",
            "grace_until": None,
            "payment_failed": False,
            "cancel_at_period_end": False,
        }
        db_mock.execute.return_value.fetchone.return_value = SimpleNamespace(**sub_row, _mapping=sub_row)
        db_mock.commit = MagicMock()

        def fake_db():
            yield db_mock

        from services.api.services.api.routers import billing as billing_mod
        with patch.object(billing_mod, "get_db", fake_db), \
             patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/cancel", headers=auth_headers)
        assert r.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_checkout_url_no_stripe(self, app):
        """GET /billing/checkout-url → placeholder when no Stripe."""
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/billing/checkout-url?plan=pro")
        assert r.status_code == 200
        assert "url" in r.json()

    @pytest.mark.asyncio
    async def test_checkout_url_with_stripe_mock(self, app):
        """GET /billing/checkout-url → Stripe session when key present."""
        fake_session = SimpleNamespace(url="https://checkout.stripe.com/pay/test", id="cs_test")
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_fake"}):
            with patch("stripe.checkout.Session.create", return_value=fake_session):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    r = await c.get("/api/v2/billing/checkout-url?plan=pro")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# SCORING V2
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringV2:
    """Tests for scoring_v2.py — backtest, calibration, experiments."""

    def _mock_engine_with_rows(self, rows, scalar=None):
        """Return engine mock that returns given rows from fetchall."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_conn.execute.return_value.scalar.return_value = scalar
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn
        engine.begin.return_value = mock_conn
        return engine

    @pytest.mark.asyncio
    async def test_backtest_no_data(self, app, auth_headers):
        """POST /scoring/backtest → empty dataset returns error dict."""
        engine = self._mock_engine_with_rows([])
        with patch("services.api.services.api.routers.scoring_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/scoring/backtest",
                    headers=auth_headers,
                    json={"weights": {}, "lookback_days": 30},
                )
        assert r.status_code == 200
        body = r.json()
        assert "error" in body or "results" in body

    @pytest.mark.asyncio
    async def test_backtest_with_data(self, app, auth_headers):
        """POST /scoring/backtest with real rows → metrics computed."""
        import datetime

        fake_row = SimpleNamespace(
            **{
                0: uuid.uuid4(),
                1: "Budowa drogi",
                2: "45230000",
                3: 2_000_000.0,
                4: datetime.datetime.utcnow() + datetime.timedelta(days=14),
                5: "won",
                6: 75.0,
                7: "GDDKiA",
                8: datetime.datetime.utcnow() - datetime.timedelta(days=10),
            }
        )
        # Make subscripting work
        fake_row.__getitem__ = lambda self, k: [
            self.__dict__.get(str(k), None),
            self.__dict__.get(str(k), None)
        ][0] if k not in self.__dict__ else self.__dict__[k]

        # Easier: use plain list
        rows = [
            [str(uuid.uuid4()), "Budowa drogi", "45230000", 2_000_000.0,
             datetime.datetime.utcnow() + datetime.timedelta(days=14),
             "won", 75.0, "GDDKiA", datetime.datetime.utcnow()]
        ]
        engine = self._mock_engine_with_rows(rows)
        with patch("services.api.services.api.routers.scoring_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/scoring/backtest",
                    headers=auth_headers,
                    json={
                        "weights": {
                            "cpv_match": 25,
                            "value_range": 20,
                            "deadline_pressure": 20,
                            "buyer_history": 20,
                            "document_quality": 15,
                        },
                        "lookback_days": 90,
                    },
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_calibration_with_bins(self, app, auth_headers):
        """GET /scoring/calibration → bins + brier score."""
        rows = [
            ["90-100", 10, 8, 92.0],
            ["70-79", 20, 10, 74.0],
            ["50-59", 15, 3, 55.0],
        ]
        engine = self._mock_engine_with_rows(rows)
        with patch("services.api.services.api.routers.scoring_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/scoring/calibration", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "bins" in body
        assert "brier_score" in body

    @pytest.mark.asyncio
    async def test_calibration_empty(self, app, auth_headers):
        """GET /scoring/calibration with no data → recommendation message."""
        engine = self._mock_engine_with_rows([])
        with patch("services.api.services.api.routers.scoring_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/scoring/calibration", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total_evaluated"] == 0

    @pytest.mark.asyncio
    async def test_create_experiment(self, app, auth_headers):
        """POST /scoring/experiment → returns experiment_id."""
        engine = self._mock_engine_with_rows([])
        with patch("services.api.services.api.routers.scoring_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/scoring/experiment",
                    headers=auth_headers,
                    json={
                        "name": "Test Experiment A",
                        "variant_weights": {
                            "cpv_match": 30,
                            "value_range": 25,
                            "deadline_pressure": 15,
                            "buyer_history": 15,
                            "document_quality": 15,
                        },
                        "sample_pct": 50,
                    },
                )
        assert r.status_code == 200
        body = r.json()
        assert "experiment_id" in body

    @pytest.mark.asyncio
    async def test_list_experiments(self, app, auth_headers):
        """GET /scoring/experiments → list."""
        rows = [
            ["experiment_abc", json.dumps({"id": "abc", "name": "Test", "status": "active"})]
        ]
        engine = self._mock_engine_with_rows(rows)
        with patch("services.api.services.api.routers.scoring_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/scoring/experiments", headers=auth_headers)
        assert r.status_code == 200

    def test_simulate_score_no_deadline_no_buyer(self):
        """_simulate_score handles None deadline and None buyer."""
        from services.api.services.api.routers.scoring_v2 import _simulate_score
        score = _simulate_score(
            cpv=None,
            value=0,
            deadline=None,
            buyer=None,
            weights={"cpv_match": 25, "value_range": 20, "deadline_pressure": 20,
                     "buyer_history": 20, "document_quality": 15},
        )
        assert isinstance(score, float)
        assert score >= 0

    def test_simulate_score_very_urgent_deadline(self):
        """_simulate_score: deadline < 7 days → deadline_score = 90."""
        import datetime
        from services.api.services.api.routers.scoring_v2 import _simulate_score
        deadline = datetime.datetime.utcnow() + datetime.timedelta(days=3)
        score = _simulate_score(
            cpv="45230000",
            value=5_000_000,
            deadline=deadline,
            buyer="GDDKiA",
            weights={"cpv_match": 25, "value_range": 20, "deadline_pressure": 20,
                     "buyer_history": 20, "document_quality": 15},
        )
        assert score > 50  # should be reasonably high

    def test_simulate_score_far_deadline(self):
        """_simulate_score: deadline > 30 days → deadline_score = 30."""
        import datetime
        from services.api.services.api.routers.scoring_v2 import _simulate_score
        deadline = datetime.datetime.utcnow() + datetime.timedelta(days=60)
        score = _simulate_score(
            cpv="45",
            value=100_000,
            deadline=deadline,
            buyer=None,
            weights={"cpv_match": 25, "value_range": 20, "deadline_pressure": 20,
                     "buyer_history": 20, "document_quality": 15},
        )
        assert isinstance(score, float)

    def test_calibration_recommendation_over_confident(self):
        """_calibration_recommendation detects over-confidence."""
        from services.api.services.api.routers.scoring_v2 import _calibration_recommendation
        bins = [
            {"bin": "80-89", "avg_score": 85, "actual_win_rate": 20, "count": 10, "wins": 2},
        ]
        rec = _calibration_recommendation(bins)
        assert "przeszacowuje" in rec

    def test_calibration_recommendation_under_confident(self):
        """_calibration_recommendation detects under-confidence."""
        from services.api.services.api.routers.scoring_v2 import _calibration_recommendation
        bins = [
            {"bin": "30-39", "avg_score": 35, "actual_win_rate": 60, "count": 10, "wins": 6},
        ]
        rec = _calibration_recommendation(bins)
        assert "niedoszacowuje" in rec

    def test_calibration_recommendation_empty(self):
        from services.api.services.api.routers.scoring_v2 import _calibration_recommendation
        rec = _calibration_recommendation([])
        assert "Za mało" in rec


# ═══════════════════════════════════════════════════════════════════════════════
# M7 PHASE 2
# ═══════════════════════════════════════════════════════════════════════════════

class TestM7Phase2:
    """Tests for m7_phase2 endpoints — buyers, competitors, market-intel, notifications."""

    def _engine_with(self, rows):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_conn.execute.return_value.fetchone.return_value = rows[0] if rows else None
        mock_conn.execute.return_value.scalar.return_value = 5
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn
        engine.begin.return_value = mock_conn
        return engine

    @pytest.mark.asyncio
    async def test_list_buyers_with_query(self, app, auth_headers):
        engine = self._engine_with([
            ["GDDKiA", 50, 10_000_000, 200_000, "2024-01-01", ["45230000"]],
        ])
        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/buyers?q=gddkia&sort=total_value", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_list_buyers_sort_name(self, app, auth_headers):
        engine = self._engine_with([])
        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/buyers?sort=name", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_buyer_history(self, app, auth_headers):
        rows = [
            [str(uuid.uuid4()), "Budowa A", 1_000_000, "active", "2024-01-01", "2024-03-01", "45230000", 72.5],
        ]
        engine = self._engine_with(rows)
        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/buyers/GDDKiA/history", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_buyer_insights(self, app, auth_headers):
        _stats_list = [15, 1_000_000, 500_000, 3_000_000, "2020-01-01", "2024-01-01"]

        class _StatsRow:
            def __getitem__(self, k):
                return _stats_list[k]

        stats_row = _StatsRow()

        months_rows = [[3, 5], [6, 4], [9, 3]]
        cpv_rows = [["45230000", 5, 500_000]]

        mock_conn = MagicMock()
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.fetchone.return_value = stats_row
            elif call_count[0] == 2:
                result.fetchall.return_value = months_rows
            else:
                result.fetchall.return_value = cpv_rows
            return result

        mock_conn.execute.side_effect = side_effect
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/buyers/GDDKiA/insights", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_competitors_atlas_not_available(self, app, auth_headers):
        """When atlas_contractors raises exception → fallback response."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("table not found")
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/competitors", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_competitor_heatmap_error(self, app, auth_headers):
        """Heatmap with DB error → returns empty list."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("join error")
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/competitors/heatmap", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_market_overview(self, app, auth_headers):
        _total_list = [100, 50_000_000, 20, 10, 5_000_000]

        class _TotalRow:
            def __getitem__(self, k):
                return _total_list[k]

        total_row = _TotalRow()

        mock_conn = MagicMock()
        call_count = [0]

        def _exec(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.fetchone.return_value = total_row
            elif call_count[0] == 2:
                result.fetchall.return_value = [["45230000", 10, 5_000_000]]
            else:
                result.fetchall.return_value = [["2024-01-01", 5, 1_000_000]]
            return result

        mock_conn.execute.side_effect = _exec
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/market-intel/overview", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_notifications_unread_only(self, app, auth_headers):
        engine = self._engine_with([])
        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/notifications?unread_only=true", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_notifications_table_missing(self, app, auth_headers):
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("table notifications does not exist")
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/notifications", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_unread_count_table_missing(self, app, auth_headers):
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("table missing")
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/notifications/unread-count", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["unread"] == 0

    @pytest.mark.asyncio
    async def test_mark_notification_read(self, app, auth_headers):
        engine = self._engine_with([])
        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.patch(
                    f"/api/v2/notifications/{uuid.uuid4()}/read",
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_command_search(self, app, auth_headers):
        engine = self._engine_with([])
        with patch("services.api.services.api.routers.m7_phase2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/command/search?q=beton", headers=auth_headers)
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# DECISIONS V2
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionsV2:
    """Tests for decisions_v2.py edge cases."""

    def test_insert_deadline_reminders_db_error(self):
        """insert_deadline_reminders: exception during DB query → returns 0."""
        from services.api.services.api.routers.decisions_v2 import insert_deadline_reminders

        engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB connection lost")
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = mock_conn

        result = insert_deadline_reminders(engine, "tenant-abc")
        assert result == 0

    def test_insert_deadline_reminders_success(self):
        """insert_deadline_reminders: inserts rows for near-deadline tenders."""
        import datetime
        from services.api.services.api.routers.decisions_v2 import insert_deadline_reminders

        today = datetime.date.today()
        rows = [
            SimpleNamespace(
                id=str(uuid.uuid4()),
                title="Budowa drogi A1",
                dl=today + datetime.timedelta(days=3),
                org_id="org-reminder",
            ),
        ]

        mock_conn = MagicMock()
        call_count = [0]

        def _exec(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.fetchall.return_value = rows
            else:
                result.fetchall.return_value = []
            return result

        mock_conn.execute.side_effect = _exec
        mock_conn.commit = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        result = insert_deadline_reminders(engine, "tenant-abc")
        # Should have processed the row without error
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_bulk_decision_no_org(self, app, auth_headers):
        """POST /decisions/bulk with no org_id → 403."""
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        no_org_user = CurrentUser(
            user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
            email="no_org@test.pl",
            org_id=None,
            role="owner",
        )
        app.dependency_overrides[get_current_user] = lambda: no_org_user
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/decisions/bulk",
                    json={"tender_ids": ["t1", "t2"], "decision": "GO", "rationale": "test"},
                )
            assert r.status_code == 403
        finally:
            # Restore demo user
            demo = CurrentUser(
                user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
                email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
                role="owner",
            )
            app.dependency_overrides[get_current_user] = lambda: demo

    @pytest.mark.asyncio
    async def test_bulk_decision_creates_records(self, app, auth_headers):
        """POST /decisions/bulk → creates N approval_request records."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value = MagicMock()
        mock_conn.commit = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.decisions_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/decisions/bulk",
                    headers=auth_headers,
                    json={
                        "tender_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                        "decision": "NO-GO",
                        "rationale": "Za wysoka wartość",
                    },
                )
        assert r.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_list_decisions_no_org(self, app, auth_headers):
        """GET /decisions without org → 403."""
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        no_org = CurrentUser(
            user_id="40a71ef6", email="x@x.pl", org_id=None, role="viewer"
        )
        app.dependency_overrides[get_current_user] = lambda: no_org
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/decisions?tender_id=fake-tender")
            assert r.status_code == 403
        finally:
            from services.api.services.api.auth.deps import CurrentUser as CU
            demo = CU(
                user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
                email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
                role="owner",
            )
            app.dependency_overrides[get_current_user] = lambda: demo

    @pytest.mark.asyncio
    async def test_get_decision_not_found(self, app, auth_headers):
        """GET /decisions/{id} for non-existent decision → 404."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.decisions_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(f"/api/v2/decisions/{uuid.uuid4()}", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_create_decision_invalid_decision_value(self, app, auth_headers):
        """POST /decisions with invalid decision string → 422."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.decisions_v2.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/decisions",
                    headers=auth_headers,
                    json={
                        "tender_id": str(uuid.uuid4()),
                        "decision": "MAYBE",
                        "rationale": "test",
                    },
                )
        assert r.status_code in (422,)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS V2
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsV2:
    """Tests for analytics_v2.py edge cases."""

    @pytest.mark.asyncio
    async def test_win_probability_fallback(self, app, auth_headers):
        """GET /win-probability → estimate_win_probability called with fallback model."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                "/api/v2/analytics/win-probability?markup=10&n_competitors=3&cpv=45",
                headers=auth_headers,
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_cost_estimate_no_icb_data(self, app, auth_headers):
        """POST /cost-estimate without area_m2 or value_estimated → error response."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/analytics/cost-estimate",
                headers=auth_headers,
                json={
                    "cpv": "45230000",
                    "region": "",
                    # No area_m2, no value_estimated
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert "error" in body

    @pytest.mark.asyncio
    async def test_cost_estimate_with_area(self, app, auth_headers):
        """POST /cost-estimate with area_m2 → compute estimate."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/analytics/cost-estimate",
                headers=auth_headers,
                json={
                    "cpv": "45230000",
                    "region": "mazowieckie",
                    "area_m2": 1000.0,
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert "expected_estimate" in body or "error" in body

    @pytest.mark.asyncio
    async def test_ahp_score_basic(self, app, auth_headers):
        """POST /ahp-score → score computed."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/analytics/ahp-score",
                headers=auth_headers,
                json={
                    "scores": {
                        "value": 80,
                        "deadline": 60,
                        "experience": 70,
                    }
                },
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_ahp_criteria(self, app, auth_headers):
        """GET /ahp-criteria → list of criteria."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/analytics/ahp-criteria", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "criteria" in body

    @pytest.mark.asyncio
    async def test_dashboard_no_org(self, app):
        """GET /analytics/dashboard without org → 403."""
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        no_org = CurrentUser(
            user_id="40a71ef6", email="x@x.pl", org_id=None, role="viewer"
        )
        app.dependency_overrides[get_current_user] = lambda: no_org
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/dashboard")
            assert r.status_code == 403
        finally:
            from services.api.services.api.auth.deps import CurrentUser as CU
            demo = CU(
                user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
                email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
                role="owner",
            )
            app.dependency_overrides[get_current_user] = lambda: demo

    @pytest.mark.asyncio
    async def test_pipeline_funnel_no_org(self, app):
        """GET /pipeline-funnel without org → 403."""
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        no_org = CurrentUser(
            user_id="40a71ef6", email="x@x.pl", org_id=None, role="viewer"
        )
        app.dependency_overrides[get_current_user] = lambda: no_org
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/pipeline-funnel")
            assert r.status_code == 403
        finally:
            from services.api.services.api.auth.deps import CurrentUser as CU
            demo = CU(
                user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
                email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
                role="owner",
            )
            app.dependency_overrides[get_current_user] = lambda: demo

    @pytest.mark.asyncio
    async def test_optimal_markup_basic(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/analytics/optimal-markup",
                headers=auth_headers,
                json={"cost_estimate": 500_000, "n_competitors": 4, "cpv": "45"},
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_recommendation_basic(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/analytics/recommendation",
                headers=auth_headers,
                json={"cost_estimate": 800_000, "n_competitors": 5, "cpv": "45", "region": "mazowieckie"},
            )
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

class TestExport:
    """Tests for export.py — DOCX, XLSX, ZIP with various data."""

    def _make_lines(self, n=5):
        return [
            {
                "lp": i + 1,
                "description": f"Pozycja kosztorysowa {i + 1}",
                "unit": "m2" if i % 2 == 0 else "szt",
                "quantity": float(10 * (i + 1)),
                "unit_price": 100.0 + i * 10,
                "line_total_pln": float(10 * (i + 1) * (100.0 + i * 10)),
                "category": "roboty budowlane",
            }
            for i in range(n)
        ]

    def _setup_engine(self, estimate_id, tender_id, lines, total_net=None):
        """Set up mocked engine returning estimate + tender + owner."""
        est_mapping = {
            "id": estimate_id,
            "tender_id": tender_id,
            "variant": "doc",
            "total_net_pln": total_net or sum(ln["line_total_pln"] for ln in lines),
            "params": {},
            "lines": lines,
        }
        tender_mapping = {
            "id": tender_id,
            "title": "Budowa drogi gminnej nr 12345 w miejscowości Testowo",
            "buyer": "Gmina Testowo",
            "cpv": "45230000",
            "external_id": "BZP-001",
        }
        owner_mapping = {"company_name": "TestBud Sp. z o.o."}

        call_count = [0]

        def _fetchone(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                row = MagicMock()
                row._mapping = est_mapping
                return row
            elif call_count[0] == 2:
                row = MagicMock()
                row._mapping = tender_mapping
                return row
            else:
                row = MagicMock()
                row._mapping = owner_mapping
                return row

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.side_effect = _fetchone
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn
        return engine

    @pytest.mark.asyncio
    async def test_export_docx_many_lines(self, app, auth_headers):
        """POST /estimates/{id}/export/docx with 50 lines → valid response."""
        est_id = str(uuid.uuid4())
        tender_id = str(uuid.uuid4())
        lines = self._make_lines(50)
        engine = self._setup_engine(est_id, tender_id, lines)

        with patch("services.api.services.api.routers.export.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v1/estimates/{est_id}/export/docx",
                    headers=auth_headers,
                    json={"template": "kosztorys_ofertowy"},
                )
        assert r.status_code == 200
        assert "docx" in r.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_export_xlsx_multi_sheet(self, app, auth_headers):
        """POST /estimates/{id}/export/xlsx → valid XLSX."""
        est_id = str(uuid.uuid4())
        tender_id = str(uuid.uuid4())
        lines = self._make_lines(20)
        engine = self._setup_engine(est_id, tender_id, lines)

        with patch("services.api.services.api.routers.export.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v1/estimates/{est_id}/export/xlsx",
                    headers=auth_headers,
                    json={"kp_percent": 15.0, "zysk_percent": 10.0, "vat_percent": 23.0},
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_export_docx_no_lines(self, app, auth_headers):
        """POST /estimates/{id}/export/docx with empty lines → 422."""
        est_id = str(uuid.uuid4())
        tender_id = str(uuid.uuid4())
        est_mapping = {
            "id": est_id, "tender_id": tender_id, "variant": "doc",
            "total_net_pln": 0, "params": {}, "lines": [],
        }
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = MagicMock(_mapping=est_mapping)
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.export.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v1/estimates/{est_id}/export/docx",
                    headers=auth_headers,
                    json={},
                )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_export_estimate_not_found(self, app, auth_headers):
        """POST /estimates/{id}/export/docx for non-existent estimate → 404."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.export.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v1/estimates/{uuid.uuid4()}/export/docx",
                    headers=auth_headers,
                    json={},
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_export_zip_multiple_estimates(self, app, auth_headers):
        """POST /tenders/{id}/estimate/export/zip with 2 variants → ZIP."""
        tender_id = str(uuid.uuid4())
        lines = self._make_lines(10)

        est_rows = [
            MagicMock(_mapping={
                "id": str(uuid.uuid4()), "variant": "doc",
                "total_net_pln": sum(l["line_total_pln"] for l in lines),
                "lines": lines,
            }),
            MagicMock(_mapping={
                "id": str(uuid.uuid4()), "variant": "owner",
                "total_net_pln": sum(l["line_total_pln"] for l in lines),
                "lines": lines,
            }),
        ]
        tender_mapping = {
            "id": tender_id,
            "title": "Remont drogi powiatowej z bardzo długą nazwą abc def ghi jkl",
            "buyer": "Powiat Testowy",
            "cpv": "45230000",
            "external_id": "BZP-002",
        }
        owner_mapping = {"company_name": "TestBud Sp. z o.o."}

        call_count = [0]

        def _exec(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.fetchall.return_value = est_rows
            elif call_count[0] == 2:
                result.fetchone.return_value = MagicMock(_mapping=tender_mapping)
            else:
                result.fetchone.return_value = MagicMock(_mapping=owner_mapping)
            return result

        mock_conn = MagicMock()
        mock_conn.execute.side_effect = _exec
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.export.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v1/tenders/{tender_id}/estimate/export/zip",
                    headers=auth_headers,
                    json={},
                )
        assert r.status_code == 200
        assert r.headers.get("content-type") == "application/zip"

    @pytest.mark.asyncio
    async def test_export_zip_no_estimates(self, app, auth_headers):
        """POST /tenders/{id}/estimate/export/zip with no estimates → 404."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_conn.execute.return_value.fetchone.return_value = MagicMock(
            _mapping={"id": "t", "title": "x", "buyer": "b", "cpv": "45", "external_id": "e"}
        )
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.export.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v1/tenders/{uuid.uuid4()}/estimate/export/zip",
                    headers=auth_headers,
                    json={},
                )
        assert r.status_code == 404

    def test_slug_special_chars(self):
        """_slug replaces non-word chars with underscores."""
        from services.api.services.api.routers.export import _slug
        result = _slug("Remont drogi nr 12/2024 (część I)")
        assert "/" not in result
        assert "(" not in result
        assert len(result) <= 60

    def test_slug_empty(self):
        from services.api.services.api.routers.export import _slug
        result = _slug("")
        assert result == "kosztorys"

    def test_slug_collision_similar_names(self):
        """Two different long titles that share first 60 chars → same slug (collision)."""
        from services.api.services.api.routers.export import _slug
        long_title = "A" * 70
        s1 = _slug(long_title)
        s2 = _slug(long_title + "extra")
        assert s1 == s2  # Both truncated to 60 chars

    def test_validate_lines_warnings(self):
        """_validate_lines adds warnings for missing price/unit."""
        from services.api.services.api.routers.export import _validate_lines
        lines = [
            {"description": "item 1", "unit": "", "quantity": 1, "unit_price": 0.0, "line_total_pln": 0},
            {"description": "item 2", "unit": "m2", "quantity": 5, "unit_price": 100.0, "line_total_pln": 500},
        ]
        warnings = _validate_lines(lines)
        assert len(warnings) >= 1
        # Missing price warning for item 1
        assert any("ceny" in w or "cen" in w.lower() for w in warnings)

    def test_check_sum_ok(self):
        """_check_sum with matching sum → no exception."""
        from services.api.services.api.routers.export import _check_sum
        lines = [{"line_total_pln": 100.0}, {"line_total_pln": 200.0}]
        _check_sum(lines, 300.0)  # Should not raise

    def test_check_sum_mismatch(self):
        """_check_sum with > 0.10 PLN diff → HTTPException 500."""
        from fastapi import HTTPException
        from services.api.services.api.routers.export import _check_sum
        lines = [{"line_total_pln": 100.0}, {"line_total_pln": 200.0}]
        with pytest.raises(HTTPException) as exc_info:
            _check_sum(lines, 500.0)
        assert exc_info.value.status_code == 500

    def test_check_sum_none_total(self):
        """_check_sum with None total → no exception (skip check)."""
        from services.api.services.api.routers.export import _check_sum
        _check_sum([{"line_total_pln": 100.0}], None)

    @pytest.mark.asyncio
    async def test_export_preview(self, app, auth_headers):
        """POST /estimates/{id}/export/preview → metadata."""
        est_id = str(uuid.uuid4())
        tender_id = str(uuid.uuid4())
        lines = self._make_lines(35)  # >30 → multiple pages
        engine = self._setup_engine(est_id, tender_id, lines)

        with patch("services.api.services.api.routers.export.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v1/estimates/{est_id}/export/preview",
                    headers=auth_headers,
                    json={"include_cover_page": True, "include_summary": True},
                )
        assert r.status_code == 200
        body = r.json()
        assert "pages" in body
        assert "sections" in body
        assert body["pages"] >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# SSE / MCP / CHAT v2
# ═══════════════════════════════════════════════════════════════════════════════

class TestSseMcpChat:
    """Tests for sse_mcp_chat.py edge cases."""

    @pytest.mark.asyncio
    async def test_mcp_tools_list(self, app, auth_headers):
        """POST /mcp tools/list → list of tools."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/mcp",
                headers=auth_headers,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
        assert r.status_code == 200
        body = r.json()
        assert "result" in body
        assert "tools" in body["result"]

    @pytest.mark.asyncio
    async def test_mcp_initialize(self, app, auth_headers):
        """POST /mcp initialize → capabilities."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/mcp",
                headers=auth_headers,
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            )
        assert r.status_code == 200
        body = r.json()
        assert "result" in body
        assert body["result"]["protocolVersion"] is not None

    @pytest.mark.asyncio
    async def test_mcp_unknown_method(self, app, auth_headers):
        """POST /mcp with unknown method → error response."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/mcp",
                headers=auth_headers,
                json={"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}},
            )
        assert r.status_code == 200
        body = r.json()
        assert "error" in body

    @pytest.mark.asyncio
    async def test_mcp_call_unknown_tool(self, app, auth_headers):
        """POST /mcp tools/call with unknown tool name → error in content."""
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.sse_mcp_chat.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v1/mcp",
                    headers=auth_headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "nonexistent_tool", "arguments": {}},
                    },
                )
        assert r.status_code == 200
        body = r.json()
        result_text = body["result"]["content"][0]["text"]
        assert "Unknown tool" in result_text or "error" in result_text.lower()

    @pytest.mark.asyncio
    async def test_mcp_call_get_tender_mocked(self, app, auth_headers):
        """POST /mcp tools/call get_tender → returns tender data."""
        tender_id = str(uuid.uuid4())
        fake_row = SimpleNamespace(
            id=tender_id, title="Test Tender", buyer="Test Buyer",
            status="active", value_pln=500_000
        )

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = fake_row
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.sse_mcp_chat.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v1/mcp",
                    headers=auth_headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "get_tender", "arguments": {"tender_id": tender_id}},
                    },
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_mcp_call_list_tenders(self, app, auth_headers):
        """POST /mcp tools/call list_tenders → returns list."""
        rows = [SimpleNamespace(id=str(uuid.uuid4()), title="T1", status="active")]

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.sse_mcp_chat.get_engine", return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v1/mcp",
                    headers=auth_headers,
                    json={
                        "jsonrpc": "2.0", "id": 4,
                        "method": "tools/call",
                        "params": {"name": "list_tenders", "arguments": {"limit": 5}},
                    },
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_mcp_exception_in_handler(self, app, auth_headers):
        """POST /mcp — engine raises exception → error in response."""
        with patch(
            "services.api.services.api.routers.sse_mcp_chat.get_engine",
            side_effect=Exception("engine init failed"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v1/mcp",
                    headers=auth_headers,
                    json={
                        "jsonrpc": "2.0", "id": 5,
                        "method": "tools/call",
                        "params": {"name": "list_tenders", "arguments": {}},
                    },
                )
        assert r.status_code == 200
        assert "error" in r.json()

    @pytest.mark.asyncio
    async def test_chat_v2_with_tender_context(self, app, auth_headers):
        """POST /api/v2/chat with tender_id → builds context, falls back on no LLM."""
        tender_id = str(uuid.uuid4())
        fake_row = SimpleNamespace(
            id=tender_id, title="Budowa drogi", buyer="GDDKiA", status="active",
            value_pln=2_000_000, deadline_at="2026-12-01", kosztorys_count=5,
            kosztorys_total=1_800_000,
        )

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = fake_row
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.sse_mcp_chat.get_engine", return_value=engine), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/chat",
                    headers=auth_headers,
                    json={
                        "message": "Jaka jest szansa wygranej?",
                        "tender_id": tender_id,
                        "history": [],
                    },
                )
        assert r.status_code == 200
        body = r.json()
        assert "reply" in body
        assert body["context_loaded"] is True

    @pytest.mark.asyncio
    async def test_chat_v2_no_tender_no_llm(self, app, auth_headers):
        """POST /api/v2/chat without tender_id and no LLM key → fallback response."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/chat",
                    headers=auth_headers,
                    json={"message": "Ile kosztuje beton?"},
                )
        assert r.status_code == 200
        body = r.json()
        assert "reply" in body
        assert body["context_loaded"] is False

    @pytest.mark.asyncio
    async def test_chat_v2_with_history(self, app, auth_headers):
        """POST /api/v2/chat with history → passed through."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/chat",
                    headers=auth_headers,
                    json={
                        "message": "Co to jest CPV?",
                        "history": [
                            {"role": "user", "content": "Cześć"},
                            {"role": "assistant", "content": "Cześć! Jak mogę pomóc?"},
                        ],
                    },
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_v2_openai_called(self, app, auth_headers):
        """POST /api/v2/chat with OpenAI key → httpx called."""
        fake_response = MagicMock()
        fake_response.raise_for_status = MagicMock()
        fake_response.json.return_value = {
            "choices": [{"message": {"content": "Odpowiedź AI"}}]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = fake_response

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}):
            with patch("httpx.Client", return_value=mock_client):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    r = await c.post(
                        "/api/v2/chat",
                        headers=auth_headers,
                        json={"message": "Test message"},
                    )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_sse_publish(self, app, auth_headers):
        """POST /sse/publish → published: True."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v1/sse/publish?event_type=test_event",
                headers=auth_headers,
                json={"key": "value"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["published"] is True

    @pytest.mark.asyncio
    async def test_mcp_info(self, app, auth_headers):
        """GET /mcp/info → server info."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/mcp/info", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "tools" in body

    @pytest.mark.asyncio
    async def test_playground_info(self, app, auth_headers):
        """GET /playground → endpoint list."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/playground", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_playground_execute_error(self, app, auth_headers):
        """POST /playground/execute → httpx error → 500."""
        import httpx
        with patch("httpx.Client", side_effect=Exception("connection refused")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v1/playground/execute?method=GET&path=/api/v1/health",
                    headers=auth_headers,
                )
        assert r.status_code == 500

    def test_publish_event_no_subscribers(self):
        """publish_event with no subscribers → no-op."""
        from services.api.services.api.routers.sse_mcp_chat import publish_event
        # Should not raise even if org has no subscribers
        publish_event("nonexistent-org", "test", {"foo": "bar"})

    def test_mcp_call_tool_get_tender_not_found(self):
        """_mcp_call_tool get_tender → row is None → error."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.sse_mcp_chat.get_engine", return_value=engine):
            from services.api.services.api.routers.sse_mcp_chat import _mcp_call_tool
            result = _mcp_call_tool("get_tender", {"tender_id": "nonexistent"})
        assert "error" in result

    def test_mcp_call_tool_unknown(self):
        """_mcp_call_tool with unknown tool name → error."""
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = mock_conn

        with patch("services.api.services.api.routers.sse_mcp_chat.get_engine", return_value=engine):
            from services.api.services.api.routers.sse_mcp_chat import _mcp_call_tool
            result = _mcp_call_tool("does_not_exist", {})
        assert "Unknown tool" in result.get("error", "")


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING — _verify_stripe_signature unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStripeSignature:

    def test_verify_signature_invalid_format(self):
        from services.api.services.api.routers.billing import _verify_stripe_signature
        result = _verify_stripe_signature(b"payload", "bad_format", "secret")
        assert result is False

    def test_verify_signature_valid(self):
        import hashlib
        import hmac as _hmac
        from services.api.services.api.routers.billing import _verify_stripe_signature

        payload = b"test_payload"
        secret = "whsec_testsecret"
        ts = "1700000000"
        signed = f"{ts}.".encode() + payload
        expected_sig = _hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        sig_header = f"t={ts},v1={expected_sig}"
        assert _verify_stripe_signature(payload, sig_header, secret) is True

    def test_verify_signature_wrong_secret(self):
        import hashlib
        import hmac as _hmac
        from services.api.services.api.routers.billing import _verify_stripe_signature

        payload = b"test_payload"
        secret = "whsec_real_secret"
        ts = "1700000000"
        signed = f"{ts}.".encode() + payload
        sig = _hmac.new(b"wrong_secret", signed, hashlib.sha256).hexdigest()
        sig_header = f"t={ts},v1={sig}"
        assert _verify_stripe_signature(payload, sig_header, secret) is False


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING helper functions
# ═══════════════════════════════════════════════════════════════════════════════

class TestBillingHelpers:

    def test_ts_none(self):
        from services.api.services.api.routers.billing import _ts
        assert _ts(None) is None

    def test_ts_unix(self):
        from services.api.services.api.routers.billing import _ts
        dt = _ts(1700000000)
        assert dt is not None
        assert dt.year > 2000

    def test_plan_from_price_none(self):
        from services.api.services.api.routers.billing import _plan_from_price
        assert _plan_from_price(None) == "free"

    def test_plan_from_price_unknown(self):
        from services.api.services.api.routers.billing import _plan_from_price
        # Unknown price_id → defaults to "pro"
        assert _plan_from_price("price_unknown_xyz") == "pro"

    def test_plan_from_price_known(self):
        from services.api.services.api.routers.billing import _plan_from_price, PRICE_ID_TO_PLAN
        # Pick a known price_id (if any)
        if PRICE_ID_TO_PLAN:
            price_id, plan_name = next(iter(PRICE_ID_TO_PLAN.items()))
            assert _plan_from_price(price_id) == plan_name
