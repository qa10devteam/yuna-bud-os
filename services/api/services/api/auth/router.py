"""Auth router — POST /api/v2/auth/register, /login, /refresh, /logout, /me."""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import hashlib
import re
from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from terra_db.session import get_session

from .deps import AuthUser
from ..services.email_service import send_welcome_email
from .utils import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from ..middleware.rate_limit import limiter

router = APIRouter(prefix="/api/v2/auth", tags=["auth"])


def get_db():
    SessionLocal = get_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB = Annotated[Session, Depends(get_db)]


# ─── schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str
    org_name: str | None = None

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Nieprawidłowy adres email")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Hasło musi mieć co najmniej 8 znaków")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class MeResponse(BaseModel):
    id: str
    email: str
    name: str
    org_id: str | None
    role: str


# ─── helpers ──────────────────────────────────────────────────────────────────

def _token_response(db: Session, user_row: Any) -> TokenResponse:
    """Create tokens, persist refresh token, return response."""
    access = create_access_token(
        user_id=str(user_row["id"]),
        email=user_row["email"],
        org_id=str(user_row["org_id"]) if user_row["org_id"] else None,
        role=user_row["role"],
    )
    raw_refresh, token_hash, expires_at = create_refresh_token()

    db.execute(
        text(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (:uid, :th, :exp)"
        ),
        {"uid": str(user_row["id"]), "th": token_hash, "exp": expires_at},
    )
    db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        user={
            "id": str(user_row["id"]),
            "email": user_row["email"],
            "name": user_row["name"],
            "org_id": str(user_row["org_id"]) if user_row["org_id"] else None,
            "role": user_row["role"],
        },
    )


def _set_auth_cookies(response: Response, access_token: str) -> None:
    """Set httpOnly session cookie + readable csrf_token cookie (double-submit pattern)."""
    csrf_token = token_urlsafe(32)
    secure = True  # set False only for local http dev via env
    response.set_cookie(
        "session",
        access_token,
        httponly=True,
        samesite="strict",
        secure=secure,
        max_age=3600,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,  # Must be readable by JS
        samesite="strict",
        secure=secure,
        max_age=3600,
        path="/",
    )


# ─── routes ───────────────────────────────────────────────────────────────────

_DEMO_TENDERS = [
    {"title": "Dostawa sprzętu komputerowego dla jednostki budżetowej",
     "buyer": "Urząd Gminy Demo", "cpv": "30213300-8", "value_pln": 120000},
    {"title": "Remont dachu budynku użyteczności publicznej",
     "buyer": "Starostwo Powiatowe Demo", "cpv": "45261910-6", "value_pln": 450000},
    {"title": "Usługi utrzymania zieleni miejskiej",
     "buyer": "Zarząd Dróg Miejskich Demo", "cpv": "77310000-6", "value_pln": 85000},
]


def _seed_new_org(db: Session, org_id: str) -> None:
    """S3-03: Create free subscription + 3 demo tenders for a freshly registered org."""
    import uuid as _uuid
    from datetime import datetime, timezone, timedelta

    # Tenant_id == org_id (production convention)
    tenant_id = org_id

    # Free subscription (bez tender_limit — nie ma tej kolumny)
    db.execute(text(
        "INSERT INTO subscription (org_id, plan, status) "
        "VALUES (:oid, 'free', 'active') "
        "ON CONFLICT (org_id) DO NOTHING"
    ), {"oid": org_id})

    # Demo tenders
    now = datetime.now(timezone.utc)
    for i, td in enumerate(_DEMO_TENDERS):
        ext_id = f"DEMO-{_uuid.uuid4().hex[:8].upper()}"
        db.execute(text(
            "INSERT INTO tender (id, title, buyer, source, external_id, published_at, deadline_at, "
            "                    value_pln, status, match_score, tenant_id) "
            "VALUES (:id, :title, :buyer, 'bzp', :ext, :pub, :dl, :val, 'new', :ms, :tid) "
            "ON CONFLICT DO NOTHING"
        ), {
            "id": str(_uuid.uuid4()),
            "title": td["title"],
            "buyer": td["buyer"],
            "ext": ext_id,
            "pub": now - timedelta(days=i),
            "dl": now + timedelta(days=30 - i * 3),
            "val": td["value_pln"],
            "ms": round(0.82 - i * 0.07, 2),
            "tid": tenant_id,
        })
    db.commit()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, body: RegisterRequest, response: Response, db: DB):
    # Check duplicate
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"), {"email": body.email}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Email już zarejestrowany")

    # Create org if name provided
    org_id = None
    if body.org_name:
        # S3-03: org.id == tenant.id (production convention — _resolve_tenant_id returns org_id)
        import uuid as _uuid
        org_id = str(_uuid.uuid4())
        db.execute(
            text("INSERT INTO tenant (id, name) VALUES (:id, :name)"),
            {"id": org_id, "name": body.org_name},
        )
        db.execute(
            text("INSERT INTO organizations (id, name, tenant_id) VALUES (:id, :name, :tid)"),
            {"id": org_id, "name": body.org_name, "tid": org_id},
        )
        db.commit()

    # Create user
    user_row = db.execute(
        text(
            """
            INSERT INTO users (email, name, password_hash, org_id, role)
            VALUES (:email, :name, :ph, :org_id, 'owner')
            RETURNING id, email, name, org_id, role
            """
        ),
        {
            "email": body.email,
            "name": body.name,
            "ph": hash_password(body.password),
            "org_id": org_id,
        },
    ).fetchone()
    db.commit()

    # S3-03: seed new org — free subscription + 3 demo tenders
    if org_id:
        _seed_new_org(db, org_id)

    # Faza 81: send welcome email
    send_welcome_email(body.email, body.name)

    token_resp = _token_response(db, user_row._mapping)
    _set_auth_cookies(response, token_resp.access_token)
    return token_resp


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, response: Response, db: DB):
    user_row = db.execute(
        text("SELECT id, email, name, password_hash, org_id, role, is_active FROM users WHERE email = :email"),
        {"email": body.email},
    ).fetchone()

    if not user_row or not verify_password(body.password, user_row.password_hash):
        raise HTTPException(status_code=401, detail="Nieprawidłowy email lub hasło")

    if not user_row.is_active:
        raise HTTPException(status_code=403, detail="Konto dezaktywowane")

    token_resp = _token_response(db, user_row._mapping)
    _set_auth_cookies(response, token_resp.access_token)
    return token_resp


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: DB):
    token_hash = hash_refresh_token(body.refresh_token)
    rt = db.execute(
        text(
            """
            SELECT rt.id, rt.user_id, rt.expires_at, rt.revoked,
                   u.email, u.name, u.org_id, u.role, u.is_active
            FROM refresh_tokens rt
            JOIN users u ON u.id = rt.user_id
            WHERE rt.token_hash = :th
            """
        ),
        {"th": token_hash},
    ).fetchone()

    if not rt:
        raise HTTPException(status_code=401, detail="Nieważny token odświeżania")
    if rt.revoked:
        raise HTTPException(status_code=401, detail="Token odświeżania unieważniony")
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token odświeżania wygasł")
    if not rt.is_active:
        raise HTTPException(status_code=403, detail="Konto dezaktywowane")

    # Revoke old refresh token
    db.execute(
        text("UPDATE refresh_tokens SET revoked = true WHERE id = :id"),
        {"id": str(rt.id)},
    )
    db.commit()

    user_dict = {
        "id": str(rt.user_id),
        "email": rt.email,
        "name": rt.name,
        "org_id": rt.org_id,
        "role": rt.role,
    }
    return _token_response(db, user_dict)


@router.post("/logout", status_code=204)
def logout(body: RefreshRequest, db: DB):
    token_hash = hash_refresh_token(body.refresh_token)
    db.execute(
        text("UPDATE refresh_tokens SET revoked = true WHERE token_hash = :th"),
        {"th": token_hash},
    )
    db.commit()


@router.get("/me", response_model=MeResponse)
def me(current_user: AuthUser):
    return MeResponse(
        id=current_user.user_id,
        email=current_user.email,
        name="",  # could fetch from DB but access token has enough info
        org_id=current_user.org_id,
        role=current_user.role,
    )
