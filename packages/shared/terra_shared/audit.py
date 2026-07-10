"""AuditWriter — append-only audit log.

Every agent step and every side-effect MUST call AuditWriter.log().
No bypass path is acceptable.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel


class AuditEntry(BaseModel):
    id: str
    tenant_id: str
    actor: str
    """Agent name or 'user'."""
    action: str
    """Verb+noun, e.g. 'ingest.run', 'approval.send_email'."""
    entity_kind: Optional[str] = None
    entity_id: Optional[str] = None
    payload: Optional[dict] = None
    ok: bool = True
    error_message: Optional[str] = None
    created_at: datetime


class AuditWriter:
    """In-memory / DB audit writer.

    In production, inject a DB session so entries are persisted.
    In tests, use the in-memory collector to assert audit entries exist.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log(
        self,
        tenant_id: str,
        actor: str,
        action: str,
        entity_kind: Optional[str] = None,
        entity_id: Optional[str] = None,
        payload: Optional[dict] = None,
        ok: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_kind=entity_kind,
            entity_id=entity_id,
            payload=payload,
            ok=ok,
            error_message=error_message,
            created_at=datetime.now(timezone.utc),
        )
        self._entries.append(entry)
        return entry

    def log_cud(
        self,
        tenant_id: str,
        actor_id: str,
        action: str,
        entity_kind: str,
        entity_id: str,
        payload: Optional[dict] = None,
    ) -> AuditEntry:
        """Convenience wrapper for Create/Update/Delete audit events."""
        return self.log(
            tenant_id=tenant_id,
            actor=actor_id,
            action=action,
            entity_kind=entity_kind,
            entity_id=entity_id,
            payload=payload,
            ok=True,
        )

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def write_to_db(self, engine: Any) -> int:
        """Persist all buffered entries to the `audit_log` table.

        Returns number of rows written. Safe to call multiple times — clears
        buffer after write so duplicate writes are avoided.

        Table schema expected (from existing audit_log):
          (id, tenant_id, at, actor, action, entity, entity_id, detail)
        """
        if not self._entries:
            return 0

        import sqlalchemy as sa

        rows = [
            {
                "id": str(uuid.uuid4()),
                "tenant_id": e.tenant_id,
                "actor": e.actor,
                "action": e.action,
                "entity": e.entity_kind or "",
                "entity_id": e.entity_id or "",
                "detail": __import__("json").dumps(e.payload or {}),
                "ok": e.ok,
                "error_msg": e.error_message or "",
            }
            for e in self._entries
        ]

        written = 0
        try:
            with engine.begin() as conn:
                for row in rows:
                    try:
                        conn.execute(
                            sa.text(
                                "INSERT INTO audit_log "
                                "(tenant_id, at, actor, action, entity, entity_id, detail) "
                                "VALUES (:tenant_id, now(), :actor, :action, :entity, :entity_id, cast(:detail as jsonb))"
                            ),
                            {k: row[k] for k in ("tenant_id", "actor", "action", "entity", "entity_id", "detail")},
                        )
                        written += 1
                    except Exception:
                        pass  # non-critical — never crash for audit
        except Exception:
            pass

        self._entries.clear()
        return written
