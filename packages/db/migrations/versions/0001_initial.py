"""M0: initial schema — all tables from spec/01_data_model.sql

Revision ID: 0001_initial
Revises: 
Create Date: 2026-06-29

Uses raw DDL to avoid SQLAlchemy enum auto-creation conflicts.
"""
from __future__ import annotations
from alembic import op

revision: str = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN CREATE TYPE tender_status AS ENUM ('new','matched','watching','analyzing','estimated','decided_go','decided_nogo','archived'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE source_kind AS ENUM ('bzp','ted','bk','bip'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE flag_severity AS ENUM ('info','warn','block'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE estimate_variant AS ENUM ('doc','owner'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE approval_status AS ENUM ('pending','approved','rejected','expired'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE agent_status AS ENUM ('queued','running','paused','succeeded','failed','cancelled'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE rfq_status AS ENUM ('draft','sent','awaiting','received','parsed','closed'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE axiom_class AS ENUM ('regulatory','documentary','engineering','economic'); EXCEPTION WHEN duplicate_object THEN null; END $$;
DO $$ BEGIN CREATE TYPE plan_status AS ENUM ('draft','dispatched','acknowledged','in_progress','done'); EXCEPTION WHEN duplicate_object THEN null; END $$;

CREATE TABLE IF NOT EXISTS tenant (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name          text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS owner_profile (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    company_name  text,
    references_md text,
    cpv_preferred text[] NOT NULL DEFAULT '{}',
    voivodeships  text[] NOT NULL DEFAULT '{}',
    equipment     jsonb NOT NULL DEFAULT '[]',
    scope_notes   text,
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tender (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    source        source_kind NOT NULL,
    external_id   text NOT NULL,
    title         text NOT NULL,
    buyer         text,
    cpv           text[] NOT NULL DEFAULT '{}',
    voivodeship   text,
    value_pln     numeric(14,2),
    deadline_at   timestamptz,
    published_at  timestamptz,
    url           text,
    status        tender_status NOT NULL DEFAULT 'new',
    match_score   numeric(5,4),
    match_reason  text,
    raw           jsonb NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, source, external_id)
);
CREATE INDEX IF NOT EXISTS ix_tender_tenant_status ON tender (tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_tender_tenant_deadline ON tender (tenant_id, deadline_at);
CREATE INDEX IF NOT EXISTS ix_tender_cpv ON tender USING gin (cpv);

CREATE TABLE IF NOT EXISTS tender_document (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    kind          text NOT NULL,
    filename      text NOT NULL,
    local_path    text NOT NULL,
    mime          text,
    pages         int,
    parsed_ok     boolean NOT NULL DEFAULT false,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_doc_tender ON tender_document (tenant_id, tender_id);

CREATE TABLE IF NOT EXISTS document_chunk (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    document_id   uuid NOT NULL REFERENCES tender_document(id),
    page          int,
    ordinal       int NOT NULL,
    content       text NOT NULL,
    embedding     vector(1024),
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chunk_doc ON document_chunk (tenant_id, document_id, ordinal);
CREATE INDEX IF NOT EXISTS ix_chunk_vec ON document_chunk USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS przedmiar_item (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    document_id   uuid REFERENCES tender_document(id),
    position_no   text,
    knr_code      text,
    description   text NOT NULL,
    unit          text,
    quantity      numeric(16,4),
    page          int,
    raw           jsonb NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_przedmiar_tender ON przedmiar_item (tenant_id, tender_id);

CREATE TABLE IF NOT EXISTS analysis (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    summary_md    text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS axiom (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    class         axiom_class NOT NULL,
    code          text NOT NULL,
    body          text NOT NULL,
    description   text,
    test_ref      text,
    version       int NOT NULL DEFAULT 1,
    active        boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code, version)
);

CREATE TABLE IF NOT EXISTS discrepancy (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    kind          text NOT NULL,
    severity      flag_severity NOT NULL,
    message       text NOT NULL,
    provenance    jsonb NOT NULL,
    axiom_id      uuid REFERENCES axiom(id),
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_discrepancy_tender ON discrepancy (tenant_id, tender_id, severity);

CREATE TABLE IF NOT EXISTS estimate (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    variant       estimate_variant NOT NULL,
    total_net_pln numeric(16,2),
    overhead_pct  numeric(6,3),
    profit_pct    numeric(6,3),
    params        jsonb NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, tender_id, variant)
);

CREATE TABLE IF NOT EXISTS estimate_line (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    estimate_id   uuid NOT NULL REFERENCES estimate(id) ON DELETE CASCADE,
    przedmiar_item_id uuid REFERENCES przedmiar_item(id),
    description   text NOT NULL,
    unit          text,
    quantity      numeric(16,4),
    unit_price    numeric(16,4),
    labor_pln     numeric(16,4),
    material_pln  numeric(16,4),
    equipment_pln numeric(16,4),
    line_total_pln numeric(16,2),
    provenance    jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_estline_estimate ON estimate_line (tenant_id, estimate_id);

CREATE TABLE IF NOT EXISTS rate_card (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    key           text NOT NULL,
    unit          text,
    rate_pln      numeric(16,4) NOT NULL,
    efficiency    numeric(10,4),
    source        text,
    valid_from    date,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, key, valid_from)
);

CREATE TABLE IF NOT EXISTS calibration_coeff (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    key           text NOT NULL,
    coeff         numeric(12,6) NOT NULL,
    variance      numeric(12,6),
    version       int NOT NULL DEFAULT 1,
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rfq (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid REFERENCES tender(id),
    scope_desc    text NOT NULL,
    status        rfq_status NOT NULL DEFAULT 'draft',
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rfq_message (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    rfq_id        uuid NOT NULL REFERENCES rfq(id) ON DELETE CASCADE,
    direction     text NOT NULL,
    counterparty  text,
    subject       text,
    body          text,
    parsed_offer  jsonb,
    message_uid   text,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_rfqmsg_rfq ON rfq_message (tenant_id, rfq_id);

CREATE TABLE IF NOT EXISTS risk_run (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    estimate_id   uuid REFERENCES estimate(id),
    samples       int NOT NULL,
    margin_p10    numeric(8,4),
    margin_p50    numeric(8,4),
    margin_p90    numeric(8,4),
    win_prob_at_price jsonb,
    drivers       jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS resource_equipment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    type text NOT NULL, model text, reg_no text, capacity jsonb, active boolean DEFAULT true
);
CREATE TABLE IF NOT EXISTS employee (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    name text NOT NULL, phone text, role text, active boolean DEFAULT true
);
CREATE TABLE IF NOT EXISTS competency (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    employee_id uuid NOT NULL REFERENCES employee(id), skill text NOT NULL, level int
);
CREATE TABLE IF NOT EXISTS availability (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    employee_id uuid REFERENCES employee(id), equipment_id uuid REFERENCES resource_equipment(id),
    day date NOT NULL, available boolean NOT NULL DEFAULT true, note text
);
CREATE TABLE IF NOT EXISTS contract (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    tender_id uuid REFERENCES tender(id), title text NOT NULL, state text NOT NULL DEFAULT 'won',
    start_date date, end_date date, location_address text, lat numeric(9,6), lng numeric(9,6),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS calendar_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    contract_id uuid REFERENCES contract(id), day date NOT NULL, title text,
    equipment_ids uuid[] DEFAULT '{}', employee_ids uuid[] DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS daily_plan (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    contract_id uuid REFERENCES contract(id), day date NOT NULL,
    location_address text, lat numeric(9,6), lng numeric(9,6),
    photos jsonb DEFAULT '[]', drawings jsonb DEFAULT '[]',
    cautions_md text, boss_note text, status plan_status NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dispatch (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    daily_plan_id uuid NOT NULL REFERENCES daily_plan(id), employee_id uuid REFERENCES employee(id),
    channel text NOT NULL, sent_at timestamptz, acknowledged_at timestamptz
);
CREATE TABLE IF NOT EXISTS field_status (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    daily_plan_id uuid REFERENCES daily_plan(id), employee_id uuid REFERENCES employee(id),
    note text, photos jsonb DEFAULT '[]', reported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mobile_device (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    employee_id uuid REFERENCES employee(id), device_token text NOT NULL UNIQUE,
    platform text, push_token text, created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approval_request (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    action text NOT NULL, payload jsonb NOT NULL, status approval_status NOT NULL DEFAULT 'pending',
    requested_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz, decided_by text
);

CREATE TABLE IF NOT EXISTS agent_run (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    agent text NOT NULL, status agent_status NOT NULL DEFAULT 'queued',
    input jsonb, output jsonb, state jsonb,
    tokens_in int DEFAULT 0, tokens_out int DEFAULT 0, cost_pln numeric(12,4) DEFAULT 0,
    started_at timestamptz, finished_at timestamptz, error text
);

CREATE TABLE IF NOT EXISTS audit_log (
    id bigserial PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenant(id),
    at timestamptz NOT NULL DEFAULT now(), actor text NOT NULL, action text NOT NULL,
    entity text, entity_id uuid, detail jsonb
);
CREATE INDEX IF NOT EXISTS ix_audit_tenant_at ON audit_log (tenant_id, at);

CREATE OR REPLACE FUNCTION audit_log_no_change()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only -- UPDATE/DELETE not allowed';
END;
$$;
DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log;
CREATE TRIGGER audit_log_no_update
    BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_no_change();
DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log;
CREATE TRIGGER audit_log_no_delete
    BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_no_change();
"""

DOWNGRADE_SQL = """
DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log;
DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log;
DROP FUNCTION IF EXISTS audit_log_no_change();
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS agent_run CASCADE;
DROP TABLE IF EXISTS approval_request CASCADE;
DROP TABLE IF EXISTS mobile_device CASCADE;
DROP TABLE IF EXISTS field_status CASCADE;
DROP TABLE IF EXISTS dispatch CASCADE;
DROP TABLE IF EXISTS daily_plan CASCADE;
DROP TABLE IF EXISTS calendar_event CASCADE;
DROP TABLE IF EXISTS contract CASCADE;
DROP TABLE IF EXISTS availability CASCADE;
DROP TABLE IF EXISTS competency CASCADE;
DROP TABLE IF EXISTS employee CASCADE;
DROP TABLE IF EXISTS resource_equipment CASCADE;
DROP TABLE IF EXISTS risk_run CASCADE;
DROP TABLE IF EXISTS rfq_message CASCADE;
DROP TABLE IF EXISTS rfq CASCADE;
DROP TABLE IF EXISTS calibration_coeff CASCADE;
DROP TABLE IF EXISTS rate_card CASCADE;
DROP TABLE IF EXISTS estimate_line CASCADE;
DROP TABLE IF EXISTS estimate CASCADE;
DROP TABLE IF EXISTS discrepancy CASCADE;
DROP TABLE IF EXISTS axiom CASCADE;
DROP TABLE IF EXISTS analysis CASCADE;
DROP TABLE IF EXISTS przedmiar_item CASCADE;
DROP TABLE IF EXISTS document_chunk CASCADE;
DROP TABLE IF EXISTS tender_document CASCADE;
DROP TABLE IF EXISTS tender CASCADE;
DROP TABLE IF EXISTS owner_profile CASCADE;
DROP TABLE IF EXISTS tenant CASCADE;
DROP TYPE IF EXISTS tender_status CASCADE;
DROP TYPE IF EXISTS source_kind CASCADE;
DROP TYPE IF EXISTS flag_severity CASCADE;
DROP TYPE IF EXISTS estimate_variant CASCADE;
DROP TYPE IF EXISTS approval_status CASCADE;
DROP TYPE IF EXISTS agent_status CASCADE;
DROP TYPE IF EXISTS rfq_status CASCADE;
DROP TYPE IF EXISTS axiom_class CASCADE;
DROP TYPE IF EXISTS plan_status CASCADE;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
