"""S103 — Multi-Tenant Onboarding: POST /api/v2/onboarding/start"""
from __future__ import annotations

import logging
from typing import List

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/onboarding", tags=["onboarding"])


class OnboardingRequest(BaseModel):
    org_name: str
    email: str
    cpv_codes: List[str] = []
    regions: List[str] = []


class OnboardingResponse(BaseModel):
    org_id: str
    tenant_id: str
    status: str


@router.post("/start", response_model=OnboardingResponse, status_code=201)
def start_onboarding(body: OnboardingRequest) -> OnboardingResponse:
    """
    S103 — Onboarding nowej organizacji (multi-tenant).
    1. INSERT INTO organizations(name) → org_id
    2. INSERT INTO tenant(org_id) → tenant_id
    3. INSERT/UPDATE scoring_config(tenant_id, cpv_codes, regions)
    4. Return {org_id, tenant_id, status: 'ready'}
    """
    engine = get_engine()
    with engine.begin() as conn:
        # 1. INSERT tenant (name required)
        tenant_row = conn.execute(
            sa.text("INSERT INTO tenant(name) VALUES (:name) RETURNING id"),
            {"name": body.org_name},
        ).fetchone()
        tenant_id = str(tenant_row[0])

        # 2. INSERT organization linked to tenant
        org_row = conn.execute(
            sa.text(
                "INSERT INTO organizations(name, tenant_id) VALUES (:name, :tid) RETURNING id"
            ),
            {"name": body.org_name, "tid": tenant_id},
        ).fetchone()
        org_id = str(org_row[0])

        # 3. INSERT or UPDATE scoring_config
        existing = conn.execute(
            sa.text("SELECT id FROM scoring_config WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).fetchone()

        if existing:
            conn.execute(
                sa.text(
                    "UPDATE scoring_config SET preferred_cpvs = :cpvs, preferred_regions = :regions "
                    "WHERE tenant_id = :tid"
                ),
                {
                    "cpvs": body.cpv_codes,
                    "regions": body.regions,
                    "tid": tenant_id,
                },
            )
        else:
            conn.execute(
                sa.text(
                    "INSERT INTO scoring_config(tenant_id, preferred_cpvs, preferred_regions) "
                    "VALUES (:tid, :cpvs, :regions)"
                ),
                {
                    "tid": tenant_id,
                    "cpvs": body.cpv_codes,
                    "regions": body.regions,
                },
            )

    logger.info("Onboarding complete: org=%s tenant=%s", org_id, tenant_id)
    return OnboardingResponse(org_id=org_id, tenant_id=tenant_id, status="ready")
