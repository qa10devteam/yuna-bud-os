"""Auth dependencies — FastAPI dependency injection for JWT auth."""
from __future__ import annotations

from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .utils import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: str, email: str, org_id: str | None, role: str):
        self.user_id = user_id
        self.email = email
        self.org_id = org_id
        self.role = role


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    """Extract and validate JWT from Authorization: Bearer <token>."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(
        user_id=payload["sub"],
        email=payload["email"],
        org_id=payload.get("org_id"),
        role=payload.get("role", "viewer"),
    )


# Convenient type alias for route signatures
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]


# ─── Faza 2 — Org/Tenant isolation ───────────────────────────────────────────

def get_tenant_id(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> str:
    """Zwraca rzeczywisty tenant_id z tabeli organizations (nie org_id).

    Wszystkie tabele domenowe (tender, rfq, approval_request, …) używają
    organizations.tenant_id — nie org_id — jako klucza izolacji.
    Używanie org_id wprost powoduje mismatch i puste wyniki list_approvals / list_tenders.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Użytkownik nie należy do żadnej organizacji",
        )
    # Resolve org_id → tenant_id via organizations table
    try:
        import sqlalchemy as _sa
        from terra_db.session import get_engine as _get_engine
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                _sa.text("SELECT tenant_id FROM organizations WHERE id = :oid LIMIT 1"),
                {"oid": current_user.org_id},
            ).fetchone()
        if row and row[0]:
            return str(row[0])
    except Exception:
        pass  # Fallback to org_id for compatibility
    # Legacy fallback: org_id == tenant_id (self-tenant orgs)
    return current_user.org_id


TenantDep = Annotated[str, Depends(get_tenant_id)]
