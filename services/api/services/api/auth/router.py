"""Auth router — POST /api/v2/auth/register, /login, /refresh, /logout, /me, /forgot-password, /reset-password."""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import hashlib
import re
import uuid as _uuid_mod
from datetime import datetime, timezone, timedelta
from secrets import token_urlsafe
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import Session

from terra_db.session import get_session, get_engine

from .deps import AuthUser
from ..services.email_service import send_welcome_email, send_password_reset_email
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
    def password_strength(cls, v: str, info) -> str:
        errors = []
        if len(v) < 12:
            errors.append("min. 12 znaków")
        if not re.search(r"[A-Z]", v):
            errors.append("min. 1 wielka litera")
        if not re.search(r"[0-9]", v):
            errors.append("min. 1 cyfra")
        if not re.search(r"[^A-Za-z0-9]", v):
            errors.append("min. 1 znak specjalny")
        # Check password != email (info.data may have email already validated)
        email_val = info.data.get("email", "")
        if email_val and v.lower() == email_val.lower():
            errors.append("hasło nie może być identyczne z adresem email")
        if errors:
            raise ValueError(f"Hasło nie spełnia wymagań: {', '.join(errors)}")
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
@limiter.limit("3/minute")
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
@limiter.limit("5/minute")
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
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: DB):
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
@limiter.limit("30/minute")
def logout(request: Request, body: RefreshRequest, db: DB):
    token_hash = hash_refresh_token(body.refresh_token)
    db.execute(
        text("UPDATE refresh_tokens SET revoked = true WHERE token_hash = :th"),
        {"th": token_hash},
    )
    db.commit()


# ─── Password Reset ────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = []
        if len(v) < 12:
            errors.append("min. 12 znaków")
        if not re.search(r"[A-Z]", v):
            errors.append("min. 1 wielka litera")
        if not re.search(r"[0-9]", v):
            errors.append("min. 1 cyfra")
        if not re.search(r"[^A-Za-z0-9]", v):
            errors.append("min. 1 znak specjalny")
        if errors:
            raise ValueError(f"Hasło nie spełnia wymagań: {', '.join(errors)}")
        return v


@router.post("/forgot-password", status_code=200)
@limiter.limit("3/hour")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: DB):
    """Generate password reset token and send email. Always returns 200 to avoid email enumeration."""
    user = db.execute(
        text("SELECT id, email FROM users WHERE email = :email"),
        {"email": body.email.lower().strip()},
    ).fetchone()

    if user:
        token = token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO password_reset_tokens (user_id, token, expires_at) "
                    "VALUES (:uid, :token, :exp)"
                ),
                {"uid": str(user.id), "token": token_hash, "exp": expires_at},
            )
        send_password_reset_email(user.email, token)

    # Always return success to prevent email enumeration
    return {"message": "Jeśli konto istnieje, wysłaliśmy link do resetowania hasła."}


@router.post("/reset-password", status_code=200)
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: DB):
    """Validate reset token and update password."""
    engine = get_engine()
    with engine.begin() as conn:
        token_hash = hashlib.sha256(body.token.encode()).hexdigest()
        row = conn.execute(
            text(
                "SELECT id, user_id, expires_at, used_at "
                "FROM password_reset_tokens "
                "WHERE token = :token"
            ),
            {"token": token_hash},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Nieprawidłowy lub wygasły token")

        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token wygasł")

        if row.used_at is not None:
            raise HTTPException(status_code=400, detail="Token został już wykorzystany")

        # Mark token as used
        conn.execute(
            text(
                "UPDATE password_reset_tokens SET used_at = now() WHERE id = :id"
            ),
            {"id": str(row.id)},
        )

        # Update password
        new_hash = hash_password(body.new_password)
        result = conn.execute(
            text("UPDATE users SET password_hash = :ph WHERE id = :uid RETURNING id"),
            {"ph": new_hash, "uid": str(row.user_id)},
        ).fetchone()

        # Revoke all existing refresh tokens for this user (session invalidation)
        conn.execute(
            text("UPDATE refresh_tokens SET revoked = true WHERE user_id = :uid AND revoked = false"),
            {"uid": str(row.user_id)},
        )

    if not result:
        raise HTTPException(status_code=400, detail="Nie znaleziono użytkownika")

    return {"message": "Hasło zostało zmienione pomyślnie."}


# ─── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=MeResponse)
def me(current_user: AuthUser):
    name = current_user.email.split('@')[0]
    return MeResponse(
        id=current_user.user_id,
        email=current_user.email,
        name=name,
        org_id=current_user.org_id,
        role=current_user.role,
    )


@router.get("/me/full")
def me_full(current_user: AuthUser):
    """Extended user profile with organization details and feature flags."""
    org_data = None
    if current_user.org_id:
        try:
            engine = get_engine()
            with engine.connect() as conn:
                org_row = conn.execute(
                    text("SELECT id, name FROM organizations WHERE id = CAST(:oid AS UUID)"),
                    {"oid": current_user.org_id},
                ).fetchone()
                if org_row:
                    org_data = {
                        "id": str(org_row.id),
                        "name": org_row.name,
                        "plan": "free",
                    }
        except Exception:
            pass
    name = current_user.email.split('@')[0]
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "name": name,
        "role": current_user.role,
        "org": org_data,
        "feature_flags": [],
    }
