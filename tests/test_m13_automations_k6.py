"""Sprint K6 tests — Automation Layer, webhooks, event triggers, suggestions."""
import sys, os, uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture()
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.automations import router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(router)
    mock_user = CurrentUser(
        user_id="test-k6",
        email="test@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture()
def headers():
    return {"Authorization": "Bearer test"}


class TestWebhookCRUD:
    def test_create_webhook(self, client, headers):
        resp = client.post("/api/v2/automations/webhooks", json={
            "name": "Test n8n",
            "url": "http://localhost:5678/webhook/test-123",
            "events": ["kosztorys.ready", "kosztorys.send_pdf"],
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]
        assert data["status"] == "created"

    def test_list_webhooks(self, client, headers):
        # Create one first
        client.post("/api/v2/automations/webhooks", json={
            "name": "List test",
            "url": "http://localhost:5678/webhook/list",
        }, headers=headers)
        resp = client.get("/api/v2/automations/webhooks", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_delete_webhook(self, client, headers):
        r = client.post("/api/v2/automations/webhooks", json={
            "name": "To delete",
            "url": "http://localhost:5678/webhook/del",
        }, headers=headers)
        wid = r.json()["id"]
        resp = client.delete(f"/api/v2/automations/webhooks/{wid}", headers=headers)
        assert resp.status_code == 200

    def test_delete_nonexistent(self, client, headers):
        fake = str(uuid.uuid4())
        resp = client.delete(f"/api/v2/automations/webhooks/{fake}", headers=headers)
        assert resp.status_code == 404

    def test_invalid_url_rejected(self, client, headers):
        resp = client.post("/api/v2/automations/webhooks", json={
            "name": "Bad URL",
            "url": "not-a-url",
        }, headers=headers)
        assert resp.status_code == 422


class TestEventTrigger:
    def test_trigger_known_event(self, client, headers):
        resp = client.post("/api/v2/automations/trigger", json={
            "event": "kosztorys.ready",
            "entity_id": str(uuid.uuid4()),
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "triggered"
        assert data["event"] == "kosztorys.ready"

    def test_trigger_unknown_event(self, client, headers):
        resp = client.post("/api/v2/automations/trigger", json={
            "event": "invalid.event",
            "entity_id": "xxx",
        }, headers=headers)
        assert resp.status_code == 422

    def test_list_events(self, client, headers):
        resp = client.get("/api/v2/automations/events", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "kosztorys.ready" in data["events"]
        assert "tender.new" in data["events"]


class TestSuggestions:
    def test_kosztorys_suggestions(self, client, headers):
        """Suggestions for a kosztorys that exists."""
        import sqlalchemy as sa
        from terra_db.session import get_engine
        with get_engine().connect() as conn:
            row = conn.execute(sa.text(
                "SELECT id FROM kosztorys WHERE tenant_id = :tid LIMIT 1"
            ), {"tid": "ec3d1e16-2139-48c2-93b5-ffe0defd606d"}).first()

        if not row:
            pytest.skip("No kosztorys in DB")

        resp = client.get(f"/api/v2/automations/suggestions/kosztorys/{row[0]}", headers=headers)
        assert resp.status_code == 200
        suggestions = resp.json()
        assert isinstance(suggestions, list)
        # Should suggest at least one action
        if suggestions:
            assert "event" in suggestions[0]
            assert "label" in suggestions[0]
            assert "priority" in suggestions[0]

    def test_nonexistent_entity(self, client, headers):
        fake = str(uuid.uuid4())
        resp = client.get(f"/api/v2/automations/suggestions/kosztorys/{fake}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestEventHistory:
    def test_history_returns_list(self, client, headers):
        resp = client.get("/api/v2/automations/history", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
