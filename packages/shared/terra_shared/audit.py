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

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)
