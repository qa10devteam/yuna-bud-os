"""SQLAlchemy 2.0 models — mirrors spec/01_data_model.sql exactly.

Conventions:
- Every operational table has tenant_id (UUID FK to tenant.id).
- Timestamps are DateTime(timezone=True) default=utcnow.
- Soft-delete via deleted_at where spec says so.
- NEVER modify this file to add business logic — models are pure schema.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# pgvector support
try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
    VECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore[assignment,misc]
    VECTOR_AVAILABLE = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    metadata = MetaData()


metadata = Base.metadata


# ─── Enums ────────────────────────────────────────────────────────────────────

tender_status_enum = Enum(
    "new", "matched", "watching", "analyzing", "estimated",
    "decided_go", "decided_nogo", "archived",
    name="tender_status",
)
source_kind_enum = Enum("bzp", "ted", "bk", "bip", name="source_kind")
flag_severity_enum = Enum("info", "warn", "block", name="flag_severity")
estimate_variant_enum = Enum("doc", "owner", name="estimate_variant")
approval_status_enum = Enum("pending", "approved", "rejected", "expired", name="approval_status")
agent_status_enum = Enum("queued", "running", "paused", "succeeded", "failed", "cancelled", name="agent_status")
rfq_status_enum = Enum("draft", "sent", "awaiting", "received", "parsed", "closed", name="rfq_status")
axiom_class_enum = Enum("regulatory", "documentary", "engineering", "economic", name="axiom_class")
plan_status_enum = Enum("draft", "dispatched", "acknowledged", "in_progress", "done", name="plan_status")


# ─── Tenant & owner profile ───────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class OwnerProfile(Base):
    __tablename__ = "owner_profile"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    company_name: Mapped[str | None] = mapped_column(Text)
    references_md: Mapped[str | None] = mapped_column(Text)
    cpv_preferred: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    voivodeships: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    equipment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    scope_notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── Tenders & documents ──────────────────────────────────────────────────────

class Tender(Base):
    __tablename__ = "tender"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source", "external_id"),
        Index("ix_tender_tenant_status", "tenant_id", "status"),
        Index("ix_tender_tenant_deadline", "tenant_id", "deadline_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    source: Mapped[str] = mapped_column(source_kind_enum, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    buyer: Mapped[str | None] = mapped_column(Text)
    cpv: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    voivodeship: Mapped[str | None] = mapped_column(Text)
    value_pln: Mapped[float | None] = mapped_column(Numeric(14, 2))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(tender_status_enum, nullable=False, default="new")
    match_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    match_reason: Mapped[str | None] = mapped_column(Text)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class TenderDocument(Base):
    __tablename__ = "tender_document"
    __table_args__ = (Index("ix_doc_tender", "tenant_id", "tender_id"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str | None] = mapped_column(Text)
    pages: Mapped[int | None] = mapped_column(Integer)
    parsed_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class DocumentChunk(Base):
    __tablename__ = "document_chunk"
    __table_args__ = (Index("ix_chunk_doc", "tenant_id", "document_id", "ordinal"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tender_document.id"), nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # embedding: vector(1024) — created via raw DDL in migration when pgvector available
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class PrzedmiarItem(Base):
    __tablename__ = "przedmiar_item"
    __table_args__ = (Index("ix_przedmiar_tender", "tenant_id", "tender_id"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"), nullable=False)
    document_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tender_document.id"))
    position_no: Mapped[str | None] = mapped_column(Text)
    knr_code: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Numeric(16, 4))
    page: Mapped[int | None] = mapped_column(Integer)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── Analysis ─────────────────────────────────────────────────────────────────

class Analysis(Base):
    __tablename__ = "analysis"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"), nullable=False)
    summary_md: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class Discrepancy(Base):
    __tablename__ = "discrepancy"
    __table_args__ = (Index("ix_discrepancy_tender", "tenant_id", "tender_id", "severity"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(flag_severity_enum, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False)
    axiom_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("axiom.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── Estimates ────────────────────────────────────────────────────────────────

class Estimate(Base):
    __tablename__ = "estimate"
    __table_args__ = (UniqueConstraint("tenant_id", "tender_id", "variant"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"), nullable=False)
    variant: Mapped[str] = mapped_column(estimate_variant_enum, nullable=False)
    total_net_pln: Mapped[float | None] = mapped_column(Numeric(16, 2))
    overhead_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    profit_pct: Mapped[float | None] = mapped_column(Numeric(6, 3))
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class EstimateLine(Base):
    __tablename__ = "estimate_line"
    __table_args__ = (Index("ix_estline_estimate", "tenant_id", "estimate_id"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    estimate_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("estimate.id", ondelete="CASCADE"), nullable=False)
    przedmiar_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("przedmiar_item.id"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Numeric(16, 4))
    unit_price: Mapped[float | None] = mapped_column(Numeric(16, 4))
    labor_pln: Mapped[float | None] = mapped_column(Numeric(16, 4))
    material_pln: Mapped[float | None] = mapped_column(Numeric(16, 4))
    equipment_pln: Mapped[float | None] = mapped_column(Numeric(16, 4))
    line_total_pln: Mapped[float | None] = mapped_column(Numeric(16, 2))
    provenance: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── Owner economic engine ────────────────────────────────────────────────────

class RateCard(Base):
    __tablename__ = "rate_card"
    __table_args__ = (UniqueConstraint("tenant_id", "key", "valid_from"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(Text)
    rate_pln: Mapped[float] = mapped_column(Numeric(16, 4), nullable=False)
    efficiency: Mapped[float | None] = mapped_column(Numeric(10, 4))
    source: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class CalibrationCoeff(Base):
    __tablename__ = "calibration_coeff"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    coeff: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    variance: Mapped[float | None] = mapped_column(Numeric(12, 6))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── RFQ / email-broker ───────────────────────────────────────────────────────

class RFQ(Base):
    __tablename__ = "rfq"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"))
    scope_desc: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(rfq_status_enum, nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class RFQMessage(Base):
    __tablename__ = "rfq_message"
    __table_args__ = (Index("ix_rfqmsg_rfq", "tenant_id", "rfq_id"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    rfq_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("rfq.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    parsed_offer: Mapped[dict | None] = mapped_column(JSONB)
    message_uid: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── Decision engine ──────────────────────────────────────────────────────────

class Axiom(Base):
    __tablename__ = "axiom"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "version"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    class_: Mapped[str] = mapped_column("class", axiom_class_enum, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    test_ref: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class RiskRun(Base):
    __tablename__ = "risk_run"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"), nullable=False)
    estimate_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("estimate.id"))
    samples: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_p10: Mapped[float | None] = mapped_column(Numeric(8, 4))
    margin_p50: Mapped[float | None] = mapped_column(Numeric(8, 4))
    margin_p90: Mapped[float | None] = mapped_column(Numeric(8, 4))
    win_prob_at_price: Mapped[dict | None] = mapped_column(JSONB)
    drivers: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── Module 3: resources, contracts, plans (Tier 3) ──────────────────────────

class ResourceEquipment(Base):
    __tablename__ = "resource_equipment"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    reg_no: Mapped[str | None] = mapped_column(Text)
    capacity: Mapped[dict | None] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Competency(Base):
    __tablename__ = "competency"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("employee.id"), nullable=False)
    skill: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[int | None] = mapped_column(Integer)


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("employee.id"))
    equipment_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("resource_equipment.id"))
    day: Mapped[datetime] = mapped_column(Date, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str | None] = mapped_column(Text)


class Contract(Base):
    __tablename__ = "contract"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    tender_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("tender.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="won")
    start_date: Mapped[datetime | None] = mapped_column(Date)
    end_date: Mapped[datetime | None] = mapped_column(Date)
    location_address: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class CalendarEvent(Base):
    __tablename__ = "calendar_event"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    contract_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("contract.id"))
    day: Mapped[datetime] = mapped_column(Date, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    equipment_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=False)), default=list)
    employee_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=False)), default=list)


class DailyPlan(Base):
    __tablename__ = "daily_plan"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    contract_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("contract.id"))
    day: Mapped[datetime] = mapped_column(Date, nullable=False)
    location_address: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    photos: Mapped[dict] = mapped_column(JSONB, default=list)
    drawings: Mapped[dict] = mapped_column(JSONB, default=list)
    cautions_md: Mapped[str | None] = mapped_column(Text)
    boss_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(plan_status_enum, nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class Dispatch(Base):
    __tablename__ = "dispatch"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    daily_plan_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("daily_plan.id"), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("employee.id"))
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FieldStatus(Base):
    __tablename__ = "field_status"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    daily_plan_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("daily_plan.id"))
    employee_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("employee.id"))
    note: Mapped[str | None] = mapped_column(Text)
    photos: Mapped[dict] = mapped_column(JSONB, default=list)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class MobileDevice(Base):
    __tablename__ = "mobile_device"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("employee.id"))
    device_token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    platform: Mapped[str | None] = mapped_column(Text)
    push_token: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ─── Cross-cutting: approvals, agents, audit ─────────────────────────────────

class ApprovalRequest(Base):
    __tablename__ = "approval_request"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(approval_status_enum, nullable=False, default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(Text)


class AgentRun(Base):
    __tablename__ = "agent_run"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    agent: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(agent_status_enum, nullable=False, default="queued")
    input: Mapped[dict | None] = mapped_column(JSONB)
    output: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[dict | None] = mapped_column(JSONB)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_pln: Mapped[float] = mapped_column(Numeric(12, 4), default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    """Append-only audit log.

    No UPDATE/DELETE allowed — enforced at app layer + DB trigger in migration.
    """
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_tenant_at", "tenant_id", "at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenant.id"), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    entity: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    detail: Mapped[dict | None] = mapped_column(JSONB)
