"""Faza 2 — Organization Management (Multi-Tenant).

Endpoints:
  GET    /api/v2/organizations/me           — profil aktualnej organizacji
  PUT    /api/v2/organizations/me           — aktualizuj profil (owner/admin)
  GET    /api/v2/organizations/me/members   — lista czlonkow
  POST   /api/v2/organizations/me/invite    — wyslij zaproszenie
  DELETE /api/v2/organizations/me/members/{user_id}  — usun czlonka (owner)
  PATCH  /api/v2/organizations/me/members/{user_id}  — zmien role (owner)
  GET    /api/v2/organizations/me/invites   — lista oczekujacych zaproszen
  DELETE /api/v2/organizations/me/invites/{invite_id} — anuluj zaproszenie
  POST   /api/v2/organizations/accept-invite/{token}  — akceptuj zaproszenie (bez auth)
"""
from __future__ import annotations


import json
import logging
from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import text

from ..auth.deps import AuthUser
from ..services.email_service import send_invite_email
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/organizations", tags=["organizations"])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]

VALID_ROLES = {"owner", "admin", "estimator", "viewer"}


# ─── helpers ──────────────────────────────────────────────────────────────────

def _require_org(user: Any) -> str:
    if not user.org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Uzytkownik nie nalezy do zadnej organizacji")
    return user.org_id


def _get_org(db: Any, org_id: str) -> dict:
    row = db.execute(
        text("SELECT id, name, nip, plan, settings, created_at FROM organizations WHERE id = :oid"),
        {"oid": org_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Organizacja nie znaleziona")
    return dict(row)


def _require_role(user: Any, *roles: str) -> None:
    if user.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Wymagana rola: {' lub '.join(roles)}",
        )


# ─── schemas ──────────────────────────────────────────────────────────────────

class OrgUpdateRequest(BaseModel):
    name: str | None = None
    nip: str | None = None
    settings: dict | None = None

    @field_validator("nip")
    @classmethod
    def nip_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        cleaned = v.replace("-", "").replace(" ", "")
        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValueError("NIP musi skladac sie z 10 cyfr")
        return cleaned


class InviteRequest(BaseModel):
    email: str
    role: str = "estimator"

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        import re
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Nieprawidlowy adres email")
        return v.lower().strip()

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Rola musi byc jedna z: {', '.join(sorted(VALID_ROLES))}")
        return v


class RoleUpdateRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Nieprawidlowa rola")
        return v


# ─── endpoints ────────────────────────────────────────────────────────────────

@router.get("/me")
def get_my_org(user: AuthUser, db: DB):
    """Profil aktualnej organizacji uzytkownika."""
    org_id = _require_org(user)
    org = _get_org(db, org_id)
    member_count = db.execute(
        text("SELECT COUNT(*) FROM users WHERE org_id = :oid AND is_active = true"),
        {"oid": org_id},
    ).scalar()
    return {
        "id": str(org["id"]),
        "name": org["name"],
        "nip": org["nip"],
        "plan": org["plan"],
        "settings": org["settings"] if org["settings"] else {},
        "member_count": member_count,
        "created_at": org["created_at"].isoformat() if org["created_at"] else None,
    }


@router.put("/me")
def update_my_org(body: OrgUpdateRequest, user: AuthUser, db: DB):
    """Aktualizuj profil organizacji (tylko owner/admin)."""
    org_id = _require_org(user)
    _require_role(user, "owner", "admin")

    updates: list[str] = []
    params: dict = {"oid": org_id}

    if body.name is not None:
        if len(body.name.strip()) < 2:
            raise HTTPException(status_code=422, detail="Nazwa musi miec min. 2 znaki")
        updates.append("name = :name")
        params["name"] = body.name.strip()

    if body.nip is not None:
        updates.append("nip = :nip")
        params["nip"] = body.nip

    if body.settings is not None:
        # Merge z istniejacymi settings
        current = _get_org(db, org_id)
        merged = {**(current["settings"] or {}), **body.settings}
        updates.append("settings = :settings")
        params["settings"] = json.dumps(merged)

    if not updates:
        raise HTTPException(status_code=422, detail="Brak pol do aktualizacji")

    db.execute(
        text(f"UPDATE organizations SET {', '.join(updates)} WHERE id = :oid"),
        params,
    )
    db.commit()
    return _get_org(db, org_id)


@router.get("/me/members")
def list_members(user: AuthUser, db: DB):
    """Lista czlonkow organizacji."""
    org_id = _require_org(user)
    rows = db.execute(
        text("""
            SELECT id, email, name, role, is_active, created_at
            FROM users
            WHERE org_id = :oid
            ORDER BY created_at ASC
        """),
        {"oid": org_id},
    ).mappings().all()
    return {
        "items": [
            {
                "id": str(r["id"]),
                "email": r["email"],
                "name": r["name"],
                "role": r["role"],
                "is_active": r["is_active"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "is_me": str(r["id"]) == user.user_id,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.post("/me/invite", status_code=status.HTTP_201_CREATED)
def invite_member(body: InviteRequest, user: AuthUser, db: DB):
    """Wyslij zaproszenie do organizacji emailem."""
    org_id = _require_org(user)
    _require_role(user, "owner", "admin")

    org = _get_org(db, org_id)

    # Sprawdz czy email juz jest czlonkiem
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email AND org_id = :oid"),
        {"email": body.email, "oid": org_id},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Uzytkownik jest juz czlonkiem organizacji")

    # Sprawdz czy zaproszenie juz istnieje i nie wygaslo
    pending = db.execute(
        text("""
            SELECT id FROM org_invites
            WHERE email = :email AND org_id = :oid
              AND accepted_at IS NULL AND expires_at > now()
        """),
        {"email": body.email, "oid": org_id},
    ).first()
    if pending:
        raise HTTPException(status_code=409,
                            detail="Zaproszenie dla tego adresu email jest juz aktywne")

    # Stworz token zaproszenia
    invite_token = token_urlsafe(32)

    # Pobierz dane zapraszajacego
    inviter = db.execute(
        text("SELECT name FROM users WHERE id = :uid"),
        {"uid": user.user_id},
    ).mappings().first()
    inviter_name = inviter["name"] if inviter else user.email

    db.execute(
        text("""
            INSERT INTO org_invites (org_id, invited_by, email, role, token)
            VALUES (:org_id, :invited_by, :email, :role, :token)
        """),
        {
            "org_id": org_id,
            "invited_by": user.user_id,
            "email": body.email,
            "role": body.role,
            "token": invite_token,
        },
    )
    db.commit()

    # Wyslij email (nie blokujemy jesli sie nie uda)
    base_url = "https://terra-os.pl"
    invite_url = f"{base_url}/dolacz?token={invite_token}"
    try:
        send_invite_email(
            to_email=body.email,
            inviter_name=inviter_name,
            org_name=org["name"],
            invite_url=invite_url,
        )
    except Exception as exc:
        logger.exception("Nie udalo sie wyslac emaila z zaproszeniem: %s", exc_info=True)

    return {
        "status": "sent",
        "email": body.email,
        "role": body.role,
        "invite_url": invite_url,
        "expires_in_days": 7,
    }


@router.get("/me/invites")
def list_invites(user: AuthUser, db: DB):
    """Lista oczekujacych zaproszen do organizacji."""
    org_id = _require_org(user)
    _require_role(user, "owner", "admin")

    rows = db.execute(
        text("""
            SELECT i.id, i.email, i.role, i.expires_at, i.created_at,
                   u.name AS invited_by_name
            FROM org_invites i
            LEFT JOIN users u ON u.id = i.invited_by
            WHERE i.org_id = :oid AND i.accepted_at IS NULL AND i.expires_at > now()
            ORDER BY i.created_at DESC
        """),
        {"oid": org_id},
    ).mappings().all()

    return {
        "items": [
            {
                "id": str(r["id"]),
                "email": r["email"],
                "role": r["role"],
                "invited_by": r["invited_by_name"],
                "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.delete("/me/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invite(invite_id: str, user: AuthUser, db: DB):
    """Anuluj zaproszenie."""
    org_id = _require_org(user)
    _require_role(user, "owner", "admin")

    result = db.execute(
        text("DELETE FROM org_invites WHERE id = :iid AND org_id = :oid"),
        {"iid": invite_id, "oid": org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Zaproszenie nie znalezione")


@router.patch("/me/members/{member_id}")
def update_member_role(member_id: str, body: RoleUpdateRequest, user: AuthUser, db: DB):
    """Zmien role czlonka organizacji (tylko owner)."""
    org_id = _require_org(user)
    _require_role(user, "owner")

    if member_id == user.user_id:
        raise HTTPException(status_code=400, detail="Nie mozesz zmienic swojej wlasnej roli")

    if body.role == "owner":
        # Transferuj ownership: aktualny owner → admin, nowy owner → owner
        # Wykluczamy member_id bo on właśnie dostanie owner
        db.execute(
            text("""
                UPDATE users SET role = 'admin'
                WHERE org_id = :oid AND role = 'owner' AND id != :member_id
            """),
            {"oid": org_id, "member_id": member_id},
        )

    result = db.execute(
        text("UPDATE users SET role = :role WHERE id = :uid AND org_id = :oid"),
        {"role": body.role, "uid": member_id, "oid": org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Czlonek nie znaleziony")

    return {"status": "updated", "user_id": member_id, "new_role": body.role}


@router.delete("/me/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(member_id: str, user: AuthUser, db: DB):
    """Usun czlonka z organizacji (tylko owner)."""
    org_id = _require_org(user)
    _require_role(user, "owner")

    if member_id == user.user_id:
        raise HTTPException(status_code=400, detail="Nie mozesz usunac siebie z organizacji")

    # Nie usuwamy - deaktywujemy i usuwamy org_id
    result = db.execute(
        text("UPDATE users SET org_id = NULL, is_active = false WHERE id = :uid AND org_id = :oid"),
        {"uid": member_id, "oid": org_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Czlonek nie znaleziony")


@router.post("/accept-invite/{token}")
def accept_invite(token: str, db: DB):
    """Akceptuj zaproszenie - uzytkownik musi sie zalogowac lub zarejestrowac z tym tokenem.

    Endpoint zwraca dane zaproszenia. Frontend przekierowuje do rejestracji/logowania z tokenem.
    Po rejestracji/logowaniu, auth router powinien sprawdzic czy jest aktywny token dla emaila.
    """
    invite = db.execute(
        text("""
            SELECT i.id, i.org_id, i.email, i.role, i.expires_at,
                   o.name AS org_name
            FROM org_invites i
            JOIN organizations o ON o.id = i.org_id
            WHERE i.token = :token AND i.accepted_at IS NULL AND i.expires_at > now()
        """),
        {"token": token},
    ).mappings().first()

    if not invite:
        raise HTTPException(status_code=404,
                            detail="Zaproszenie nie znalezione lub wygaslo")

    return {
        "email": invite["email"],
        "org_id": str(invite["org_id"]),
        "org_name": invite["org_name"],
        "role": invite["role"],
        "expires_at": invite["expires_at"].isoformat(),
        "token": token,
    }
