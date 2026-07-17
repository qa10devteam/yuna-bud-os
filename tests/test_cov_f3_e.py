"""F3-E: Unit tests for system.py, notifications.py, organizations.py.
Mock get_engine/get_db to avoid real DB.
"""
from __future__ import annotations
import uuid
import json

from unittest.mock import MagicMock as _MagicMock
_MOCK_USER = _MagicMock()
_MOCK_USER.user_id = "test-user-id"
_MOCK_USER.org_id = "test-org-id"
_MOCK_USER.role = "owner"

from unittest.mock import patch, MagicMock
import pytest

MOD_SYS = "services.api.services.api.routers.system"
MOD_NOTIF = "services.api.services.api.routers.notifications"
MOD_ORG = "services.api.services.api.routers.organizations"


def _mock_engine(rows=None, fetchone=None):
    """Create a mock engine. rows=list for fetchall, fetchone=tuple for single."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value.__enter__ = lambda s: conn
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)

    result = MagicMock()
    if fetchone is not None:
        result.fetchone.return_value = fetchone
    elif rows is not None:
        result.fetchone.return_value = rows[0] if rows else None
        result.fetchall.return_value = rows
    else:
        result.fetchone.return_value = None
        result.fetchall.return_value = []
    result.rowcount = 1
    conn.execute.return_value = result
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# system.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_agent_run_found():
    """Line 85: agent run found → return response."""
    from services.api.services.api.routers.system import get_agent_run
    row = (str(uuid.uuid4()), "pipeline_supervisor", "succeeded", 100, 50, 0.25, None)
    engine = _mock_engine(fetchone=row)
    with patch(f"{MOD_SYS}.get_engine", return_value=engine):
        result = get_agent_run("test-id", _MOCK_USER)
    assert result.status == "succeeded"
    assert result.tokens_in == 100


def test_transition_agent_found():
    """Lines 101-105: agent transition → update status."""
    from services.api.services.api.routers.system import _transition_agent
    row = (str(uuid.uuid4()), "running")
    engine = _mock_engine(fetchone=row)
    with patch(f"{MOD_SYS}.get_engine", return_value=engine):
        result = _transition_agent("test-id", "paused")
    assert result == {"ok": True, "status": "paused"}


def test_resume_agent():
    """Line 115."""
    from services.api.services.api.routers.system import resume_agent
    row = (str(uuid.uuid4()), "paused")
    engine = _mock_engine(fetchone=row)
    with patch(f"{MOD_SYS}.get_engine", return_value=engine):
        result = resume_agent("test-id", _MOCK_USER)
    assert result["status"] == "running"


def test_cancel_agent():
    """Line 120."""
    from services.api.services.api.routers.system import cancel_agent
    row = (str(uuid.uuid4()), "running")
    engine = _mock_engine(fetchone=row)
    with patch(f"{MOD_SYS}.get_engine", return_value=engine):
        result = cancel_agent("test-id", _MOCK_USER)
    assert result["status"] == "cancelled"


def test_trigger_pipeline():
    """Lines 130-147: trigger pipeline."""
    from services.api.services.api.routers.system import trigger_pipeline
    tenant_row = (str(uuid.uuid4()),)
    engine = _mock_engine(fetchone=tenant_row)
    with patch(f"{MOD_SYS}.get_engine", return_value=engine), \
         patch(f"{MOD_SYS}._run_pipeline_sync"):
        result = trigger_pipeline(_MOCK_USER)
    assert "agent_run_id" in result


def test_run_pipeline_sync_success():
    """Lines 152-167: pipeline succeeds."""
    from services.api.services.api.routers.system import _run_pipeline_sync
    engine = _mock_engine()
    with patch(f"{MOD_SYS}.get_engine", return_value=engine), \
         patch("services.agents.pipeline.run_pipeline", return_value={"steps": 5}), \
         patch("services.agents.pipeline.PipelineState"):
        _run_pipeline_sync("run-1", "tenant-1")


def test_run_pipeline_sync_error():
    """Lines 168-172: pipeline raises exception."""
    from services.api.services.api.routers.system import _run_pipeline_sync
    engine = _mock_engine()
    with patch(f"{MOD_SYS}.get_engine", return_value=engine), \
         patch("services.agents.pipeline.run_pipeline", side_effect=RuntimeError("boom")), \
         patch("services.agents.pipeline.PipelineState"):
        _run_pipeline_sync("run-1", "tenant-1")


def test_close_contract_endpoint():
    """Lines 182-194: close contract."""
    from services.api.services.api.routers.system import close_contract_endpoint, ContractCloseRequest
    contract_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    row = (contract_id, tenant_id)
    engine = _mock_engine(fetchone=row)
    body = ContractCloseRequest(actual_cost_pln=50000.0)
    mock_close = MagicMock(return_value={"status": "closed"})
    with patch(f"{MOD_SYS}.get_engine", return_value=engine), \
         patch("services.agents.learning_loop.close_contract", mock_close):
        result = close_contract_endpoint(contract_id, body, _MOCK_USER)
    assert result is not None


def test_backup_status():
    """Lines 207-214: backup status."""
    from services.api.services.api.routers.system import backup_status
    row = ("2025-07-16 10:00:00", "completed", 1024000)
    engine = _mock_engine(fetchone=row)
    mock_user = MagicMock()
    mock_user.role = "owner"
    with patch(f"{MOD_SYS}.get_engine", return_value=engine):
        result = backup_status(user=mock_user)
    assert result is not None


def test_run_backup_endpoint():
    """Lines 220-263: trigger backup."""
    from services.api.services.api.routers.system import run_backup
    engine = _mock_engine()
    mock_user = MagicMock()
    mock_user.role = "owner"
    with patch(f"{MOD_SYS}.get_engine", return_value=engine), \
         patch(f"{MOD_SYS}.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=0, stdout="OK")
        result = run_backup(user=mock_user)
    assert result is not None


def test_get_version():
    """Lines 272-273."""
    from services.api.services.api.routers.system import get_version
    result = get_version()
    assert "version" in result


def test_health_detailed():
    """Lines 287-322: detailed health check."""
    from services.api.services.api.routers.system import health_detailed
    engine = _mock_engine(fetchone=(1,))
    with patch(f"{MOD_SYS}.get_engine", return_value=engine):
        result = health_detailed()
    assert result is not None


def test_read_audit():
    """Lines 333-356: audit log — no user param, uses tenant query."""
    from services.api.services.api.routers.system import read_audit
    rows = [
        (1, "2025-07-16", "user@test.com", "login", "session", str(uuid.uuid4()), None),
        (2, "2025-07-15", "admin@test.com", "update_org", "org", str(uuid.uuid4()), '{"field":"name"}'),
    ]
    engine = _mock_engine(rows=rows)
    with patch(f"{MOD_SYS}.get_engine", return_value=engine):
        result = read_audit(_MOCK_USER)
    assert len(result) == 2


def test_get_version_v2():
    """Line 373: v2 version endpoint."""
    from services.api.services.api.routers.system import get_version_v2
    result = get_version_v2()
    assert "version" in result


# ═══════════════════════════════════════════════════════════════════════════════
# notifications.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_unread_count():
    """Lines 63-78: unread count."""
    from services.api.services.api.routers.notifications import unread_count
    engine = _mock_engine(fetchone=(5,))
    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    with patch(f"{MOD_NOTIF}.get_engine", return_value=engine):
        result = unread_count(user=mock_user)
    assert result is not None


def test_mark_all_read():
    """Lines 130-145: mark all as read."""
    from services.api.services.api.routers.notifications import mark_all_read
    engine = _mock_engine()
    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    with patch(f"{MOD_NOTIF}.get_engine", return_value=engine):
        result = mark_all_read(user=mock_user)
    assert result is not None


def test_list_notifications():
    """Lines 149-199: list notifications with cursor pagination."""
    from services.api.services.api.routers.notifications import list_notifications
    from datetime import datetime
    row = MagicMock()
    row.id = str(uuid.uuid4())
    row.type = "tender_alert"
    row.title = "New tender"
    row.body = "Details"
    row.read = False
    row.link = None
    row.created_at = datetime(2025, 7, 16, 10, 0)
    engine = _mock_engine(rows=[row])
    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    with patch(f"{MOD_NOTIF}.get_engine", return_value=engine):
        result = list_notifications(user=mock_user, limit=50, cursor=None)
    assert result is not None


def test_mark_read():
    """Lines 201-225: mark single notification read."""
    from services.api.services.api.routers.notifications import mark_read
    engine = _mock_engine(fetchone=(1,))
    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    with patch(f"{MOD_NOTIF}.get_engine", return_value=engine):
        result = mark_read(notification_id=str(uuid.uuid4()), user=mock_user)
    assert result is not None


def test_put_mark_read():
    """Lines 227-250."""
    from services.api.services.api.routers.notifications import put_mark_read
    engine = _mock_engine(fetchone=(1,))
    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    with patch(f"{MOD_NOTIF}.get_engine", return_value=engine):
        result = put_mark_read(notification_id=str(uuid.uuid4()), user=mock_user)
    assert result is not None


def test_delete_notification():
    """Lines 252-281: delete notification."""
    from services.api.services.api.routers.notifications import delete_notification
    engine = _mock_engine(fetchone=(str(uuid.uuid4()),))
    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    mock_user.org_id = str(uuid.uuid4())
    with patch(f"{MOD_NOTIF}.get_engine", return_value=engine):
        delete_notification(notification_id=str(uuid.uuid4()), user=mock_user)


def test_bulk_read():
    """Lines 283+."""
    from services.api.services.api.routers.notifications import bulk_read, BulkReadRequest
    engine = _mock_engine()
    mock_user = MagicMock()
    mock_user.user_id = str(uuid.uuid4())
    body = BulkReadRequest(ids=[str(uuid.uuid4()), str(uuid.uuid4())])
    with patch(f"{MOD_NOTIF}.get_engine", return_value=engine):
        result = bulk_read(body=body, user=mock_user)
    assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# organizations.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_org_no_org_id():
    """User without org_id → 400 (not org member)."""
    from services.api.services.api.routers.organizations import _require_org
    from fastapi import HTTPException
    mock_user = MagicMock()
    mock_user.org_id = None
    with pytest.raises(HTTPException) as exc_info:
        _require_org(mock_user)
    assert exc_info.value.status_code == 400


def test_get_my_org():
    """Lines 127-145: get current org."""
    from services.api.services.api.routers.organizations import get_my_org
    mock_db = MagicMock()
    org_row = {"id": str(uuid.uuid4()), "name": "QA10", "nip": "9542906279",
               "plan": "starter", "settings": {}, "created_at": None}
    mock_db.execute.return_value.mappings.return_value.first.return_value = org_row
    mock_db.execute.return_value.scalar.return_value = 3
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    result = get_my_org(user=mock_user, db=mock_db)
    assert result["name"] == "QA10"


def test_update_my_org():
    """Lines 147-182: update org."""
    from services.api.services.api.routers.organizations import update_my_org, OrgUpdateRequest
    mock_db = MagicMock()
    mock_db.execute.return_value = MagicMock(rowcount=1)
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    mock_user.role = "owner"
    body = OrgUpdateRequest(name="New Name")
    result = update_my_org(body=body, user=mock_user, db=mock_db)
    assert result is not None


def test_list_members():
    """Lines 184-212: list org members."""
    from services.api.services.api.routers.organizations import list_members
    mock_db = MagicMock()
    rows = [
        MagicMock(id=str(uuid.uuid4()), email="a@b.com", role="member", joined_at="2025-01-01"),
        MagicMock(id=str(uuid.uuid4()), email="c@d.com", role="owner", joined_at="2024-01-01"),
    ]
    mock_db.execute.return_value = MagicMock(fetchall=lambda: rows)
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    result = list_members(user=mock_user, db=mock_db)
    assert result is not None


def test_invite_member():
    """Lines 214-288: invite member — mock DB returns None for existing checks."""
    from services.api.services.api.routers.organizations import invite_member, InviteRequest
    mock_db = MagicMock()
    # _get_org: mappings().first() → org dict
    org_row = {"id": str(uuid.uuid4()), "name": "QA10", "nip": "9542906279",
               "plan": "starter", "settings": {}, "created_at": None}
    inviter_row = {"name": "Mateusz"}

    call_count = {"n": 0}
    def side_effect(query, params=None):
        res = MagicMock()
        call_count["n"] += 1
        n = call_count["n"]
        if n == 1:  # _get_org
            res.mappings.return_value.first.return_value = org_row
        elif n == 2:  # existing user check → None
            res.first.return_value = None
        elif n == 3:  # pending invite check → None
            res.first.return_value = None
        elif n == 4:  # inviter name lookup
            res.mappings.return_value.first.return_value = inviter_row
        else:
            res.first.return_value = None
            res.mappings.return_value.first.return_value = None
        return res
    mock_db.execute.side_effect = side_effect
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    mock_user.role = "owner"
    mock_user.email = "admin@qa10.io"
    body = InviteRequest(email="new@test.com", role="estimator")
    with patch(f"{MOD_ORG}.send_invite_email", return_value=None):
        result = invite_member(body=body, user=mock_user, db=mock_db)
    assert result is not None


def test_list_invites():
    """Lines 290-322: list pending invites — needs owner/admin role."""
    from services.api.services.api.routers.organizations import list_invites
    mock_db = MagicMock()
    mock_db.execute.return_value.mappings.return_value.all.return_value = []
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    mock_user.role = "owner"
    result = list_invites(user=mock_user, db=mock_db)
    assert result["total"] == 0


def test_cancel_invite():
    """Lines 324-337: cancel invite returns None (204)."""
    from services.api.services.api.routers.organizations import cancel_invite
    mock_db = MagicMock()
    mock_db.execute.return_value.rowcount = 1
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    mock_user.role = "owner"
    result = cancel_invite(invite_id=str(uuid.uuid4()), user=mock_user, db=mock_db)
    assert result is None  # 204 No Content


def test_update_member_role():
    """Lines 339-368: update member role."""
    from services.api.services.api.routers.organizations import update_member_role, RoleUpdateRequest
    mock_db = MagicMock()
    mock_db.execute.return_value.rowcount = 1
    member_id = str(uuid.uuid4())
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    mock_user.role = "owner"
    mock_user.user_id = str(uuid.uuid4())  # different from member_id
    body = RoleUpdateRequest(role="admin")
    result = update_member_role(member_id=member_id, body=body, user=mock_user, db=mock_db)
    assert result["new_role"] == "admin"


def test_remove_member():
    """Lines 370-387: remove member returns None (204)."""
    from services.api.services.api.routers.organizations import remove_member
    mock_db = MagicMock()
    mock_db.execute.return_value.rowcount = 1
    member_id = str(uuid.uuid4())
    mock_user = MagicMock()
    mock_user.org_id = str(uuid.uuid4())
    mock_user.role = "owner"
    mock_user.user_id = str(uuid.uuid4())  # different from member_id
    result = remove_member(member_id=member_id, user=mock_user, db=mock_db)
    assert result is None  # 204 No Content


def test_accept_invite():
    """Lines 389+: accept invite by token."""
    from services.api.services.api.routers.organizations import accept_invite
    from datetime import datetime, timezone
    mock_db = MagicMock()
    invite_data = {
        "id": str(uuid.uuid4()), "org_id": str(uuid.uuid4()),
        "email": "new@test.com", "role": "estimator",
        "expires_at": datetime(2099, 12, 31, tzinfo=timezone.utc),
        "org_name": "QA10",
    }
    mock_db.execute.return_value.mappings.return_value.first.return_value = invite_data
    result = accept_invite(token=str(uuid.uuid4()), db=mock_db)
    assert result is not None
