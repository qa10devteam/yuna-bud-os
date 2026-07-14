"""P3-7 — Tests for celery_app.py and tasks.py.

Strategy:
  - Test that celery_app module imports cleanly and is configured correctly.
  - Mock Celery broker/backend entirely; never actually connect to Redis.
  - Test task *logic* by calling internal helper functions directly (not .delay()).
  - For tasks that call external deps (DB, ingestion), patch those and verify
    the correct return values / retry behaviour.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch, call
import pytest

# Ensure vendor path is present (celery_app.py prepends it)
VENDOR_PATH = os.path.join(
    os.path.dirname(__file__), "..", "packages", "vendor"
)


# ── Module import tests ────────────────────────────────────────────────────────

class TestCeleryAppImport:
    def test_celery_app_imports_cleanly(self):
        """celery_app module can be imported without a live Redis/broker."""
        # The module is expected to import without errors even if Redis is absent.
        import importlib
        import services.api.services.api.celery_app as celery_module
        assert celery_module is not None

    def test_celery_app_object_exists(self):
        """celery_app is a Celery instance."""
        from celery import Celery
        from services.api.services.api.celery_app import celery_app
        assert isinstance(celery_app, Celery)

    def test_app_name_is_terra(self):
        from services.api.services.api.celery_app import celery_app
        assert celery_app.main == "terra"

    def test_queues_configured(self):
        """critical, normal, batch queues are registered."""
        from services.api.services.api.celery_app import celery_app
        queue_names = {q.name for q in celery_app.conf.task_queues}
        assert "critical" in queue_names
        assert "normal" in queue_names
        assert "batch" in queue_names

    def test_default_queue_is_normal(self):
        from services.api.services.api.celery_app import celery_app
        assert celery_app.conf.task_default_queue == "normal"

    def test_serialization_is_json(self):
        from services.api.services.api.celery_app import celery_app
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

    def test_beat_schedule_contains_bzp_sync(self):
        from services.api.services.api.celery_app import celery_app
        schedule = celery_app.conf.beat_schedule
        assert "sync-bzp-every-15-min" in schedule
        task_entry = schedule["sync-bzp-every-15-min"]
        assert task_entry["schedule"] == 900.0

    def test_utc_enabled(self):
        from services.api.services.api.celery_app import celery_app
        assert celery_app.conf.enable_utc is True


# ── tasks.py import ────────────────────────────────────────────────────────────

class TestTasksImport:
    def test_tasks_module_imports_cleanly(self):
        import services.api.services.api.tasks as tasks_module
        assert tasks_module is not None

    def test_all_expected_tasks_registered(self):
        """All four main tasks are importable from tasks module."""
        from services.api.services.api.tasks import (
            sync_bzp_task,
            process_document_task,
            run_analysis_task,
            fire_tender_alerts,
            notify_task,
        )
        assert sync_bzp_task is not None
        assert process_document_task is not None
        assert run_analysis_task is not None
        assert fire_tender_alerts is not None
        assert notify_task is not None

    def test_task_names_are_correct(self):
        from services.api.services.api.tasks import (
            sync_bzp_task,
            process_document_task,
            run_analysis_task,
            fire_tender_alerts,
            notify_task,
        )
        assert sync_bzp_task.name == "services.api.services.api.tasks.sync_bzp_task"
        assert process_document_task.name == "services.api.services.api.tasks.process_document_task"
        assert run_analysis_task.name == "services.api.services.api.tasks.run_analysis_task"
        assert fire_tender_alerts.name == "services.api.services.api.tasks.fire_tender_alerts"
        assert notify_task.name == "services.api.services.api.tasks.notify_task"


# ── process_document_task logic ────────────────────────────────────────────────

class TestProcessDocumentTask:
    def test_happy_path_returns_ok(self):
        """process_document_task returns ok dict on success."""
        from services.api.services.api.tasks import process_document_task

        doc_id = "doc-123"
        org_id = "org-456"

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        # .run is already bound to the task instance — no mock_self needed
        with patch("terra_db.session.get_engine", return_value=mock_engine):
            result = process_document_task.run(doc_id, org_id)

        assert result["status"] == "ok"
        assert result["document_id"] == doc_id

    def test_error_triggers_retry(self):
        """process_document_task calls self.retry on DB error."""
        from services.api.services.api.tasks import process_document_task

        mock_engine = MagicMock()
        mock_engine.connect.side_effect = RuntimeError("DB down")

        retry_exc = Exception("retry called")
        with patch.object(process_document_task, "retry", side_effect=retry_exc):
            with patch("terra_db.session.get_engine", return_value=mock_engine):
                with pytest.raises(Exception, match="retry called"):
                    process_document_task.run("doc-x", "org-x")


# ── run_analysis_task logic ────────────────────────────────────────────────────

class TestRunAnalysisTask:
    def _make_conn(self, tender_row=None):
        conn = MagicMock()

        def _execute(stmt, params=None):
            sql = str(stmt)
            res = MagicMock()
            if "SELECT id, title, tenant_id" in sql:
                res.fetchone.return_value = tender_row
            else:
                res.fetchone.return_value = None
            return res

        conn.execute = MagicMock(side_effect=_execute)
        conn.commit = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        engine = MagicMock()
        engine.connect.return_value = conn
        return engine

    def test_tender_not_found_returns_error(self):
        """run_analysis_task returns error when tender is missing."""
        from services.api.services.api.tasks import run_analysis_task

        engine = self._make_conn(tender_row=None)

        with patch("terra_db.session.get_engine", return_value=engine):
            result = run_analysis_task.run("missing-tender", "org-1")

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_tender_found_returns_ok(self):
        """run_analysis_task returns ok and tender_id when tender exists."""
        from services.api.services.api.tasks import run_analysis_task

        tender_row = MagicMock()
        tender_row.id = "tender-1"
        tender_row.title = "Test Tender"
        tender_row.tenant_id = "tenant-1"

        engine = self._make_conn(tender_row=tender_row)

        with patch("terra_db.session.get_engine", return_value=engine):
            result = run_analysis_task.run("tender-1", "org-1")

        assert result["status"] == "ok"
        assert result["tender_id"] == "tender-1"

    def test_db_error_triggers_retry(self):
        """run_analysis_task calls self.retry on exception."""
        from services.api.services.api.tasks import run_analysis_task

        mock_engine = MagicMock()
        mock_engine.connect.side_effect = RuntimeError("connection refused")

        with patch.object(run_analysis_task, "retry", side_effect=Exception("retry!")):
            with patch("terra_db.session.get_engine", return_value=mock_engine):
                with pytest.raises(Exception, match="retry!"):
                    run_analysis_task.run("t-err", "o-err")


# ── notify_task logic ──────────────────────────────────────────────────────────

class TestNotifyTask:
    def test_happy_path_returns_ok(self):
        """notify_task inserts notification row and returns ok."""
        from services.api.services.api.tasks import notify_task

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("terra_db.session.get_engine", return_value=mock_engine):
            result = notify_task(
                user_id="user-1",
                org_id="org-1",
                notif_type="alert",
                title="Test",
                body="body text",
                link="/test",
            )

        assert result["status"] == "ok"
        mock_conn.execute.assert_called_once()

    def test_db_error_returns_error_dict(self):
        """notify_task returns error dict on DB exception (no retry)."""
        from services.api.services.api.tasks import notify_task

        mock_engine = MagicMock()
        mock_engine.connect.side_effect = RuntimeError("DB error")

        with patch("terra_db.session.get_engine", return_value=mock_engine):
            result = notify_task(
                user_id="u", org_id="o", notif_type="t", title="T"
            )

        assert result["status"] == "error"
        assert "DB error" in result["message"]


# ── fire_tender_alerts logic ───────────────────────────────────────────────────

class TestFireTenderAlerts:
    def test_happy_path_returns_ok(self):
        """fire_tender_alerts delegates to run_alert_runner and returns ok."""
        from services.api.services.api.tasks import fire_tender_alerts

        mock_stats = {"sent": 3, "skipped": 1}

        # run_alert_runner is lazily imported inside the task body
        with patch("services.ingestion.alert_runner.run_alert_runner", return_value=mock_stats):
            result = fire_tender_alerts.run(tenant_id="t1", frequency="daily")

        assert result["status"] == "ok"
        assert result["sent"] == 3
        assert result["skipped"] == 1

    def test_error_triggers_retry(self):
        """fire_tender_alerts retries on exception."""
        from services.api.services.api.tasks import fire_tender_alerts

        with patch.object(fire_tender_alerts, "retry", side_effect=Exception("retry!")):
            with patch(
                "services.ingestion.alert_runner.run_alert_runner",
                side_effect=RuntimeError("alert_runner exploded"),
            ):
                with pytest.raises(Exception, match="retry!"):
                    fire_tender_alerts.run()
