-- =====================================================================
-- Terra.OS — canonical data model (PostgreSQL 16 + pgvector)
-- Authoritative DDL. Generate Alembic migrations to match this file.
-- Conventions: snake_case; every operational table has tenant_id;
-- timestamps are timestamptz default now(); soft-delete via deleted_at where noted.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

-- ---------- enums ----------
CREATE TYPE tender_status   AS ENUM ('new','matched','watching','analyzing','estimated','decided_go','decided_nogo','archived');
CREATE TYPE source_kind     AS ENUM ('bzp','ted','bk','bip');
CREATE TYPE flag_severity   AS ENUM ('info','warn','block');
CREATE TYPE estimate_variant AS ENUM ('doc','owner');         -- A=doc-based, B=owner economic engine
CREATE TYPE approval_status AS ENUM ('pending','approved','rejected','expired');
CREATE TYPE agent_status    AS ENUM ('queued','running','paused','succeeded','failed','cancelled');
CREATE TYPE rfq_status      AS ENUM ('draft','sent','awaiting','received','parsed','closed');
CREATE TYPE axiom_class     AS ENUM ('regulatory','documentary','engineering','economic');
CREATE TYPE plan_status     AS ENUM ('draft','dispatched','acknowledged','in_progress','done');

-- ---------- tenancy & owner profile ----------
CREATE TABLE tenant (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name          text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE owner_profile (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    company_name  text,
    references_md text,                       -- experience / references narrative
    cpv_preferred text[] NOT NULL DEFAULT '{}',-- e.g. {45111200,45112000}
    voivodeships  text[] NOT NULL DEFAULT '{}',-- {dolnoslaskie,slaskie,opolskie,lubuskie}
    equipment     jsonb NOT NULL DEFAULT '[]', -- [{type,model,count}]
    scope_notes   text,
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------- tenders & documents ----------
CREATE TABLE tender (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    source        source_kind NOT NULL,
    external_id   text NOT NULL,              -- id within source
    title         text NOT NULL,
    buyer         text,
    cpv           text[] NOT NULL DEFAULT '{}',
    voivodeship   text,
    value_pln     numeric(14,2),
    deadline_at   timestamptz,
    published_at  timestamptz,
    url           text,
    status        tender_status NOT NULL DEFAULT 'new',
    match_score   numeric(5,4),              -- 0..1 owner fit
    match_reason  text,
    raw           jsonb NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, source, external_id)
);
CREATE INDEX ix_tender_tenant_status ON tender (tenant_id, status);
CREATE INDEX ix_tender_tenant_deadline ON tender (tenant_id, deadline_at);
CREATE INDEX ix_tender_cpv ON tender USING gin (cpv);

CREATE TABLE tender_document (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    kind          text NOT NULL,             -- swz|design|stwior|przedmiar|other
    filename      text NOT NULL,
    local_path    text NOT NULL,
    mime          text,
    pages         int,
    parsed_ok     boolean NOT NULL DEFAULT false,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_doc_tender ON tender_document (tenant_id, tender_id);

CREATE TABLE document_chunk (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    document_id   uuid NOT NULL REFERENCES tender_document(id),
    page          int,
    ordinal       int NOT NULL,
    content       text NOT NULL,
    embedding     vector(1024),              -- local embedding dim; set to model dim
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_chunk_doc ON document_chunk (tenant_id, document_id, ordinal);
CREATE INDEX ix_chunk_vec ON document_chunk USING hnsw (embedding vector_cosine_ops);

CREATE TABLE przedmiar_item (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    document_id   uuid REFERENCES tender_document(id),
    position_no   text,                      -- e.g. "1.2.3"
    knr_code      text,                      -- KNR/KNNR mapping if available
    description   text NOT NULL,
    unit          text,                      -- m3, m2, mb, t, szt
    quantity      numeric(16,4),
    page          int,
    raw           jsonb NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_przedmiar_tender ON przedmiar_item (tenant_id, tender_id);

-- ---------- analysis outputs (summaries, red-flags, discrepancies) ----------
CREATE TABLE analysis (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    summary_md    text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE discrepancy (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    kind          text NOT NULL,             -- missing_in_design|missing_in_przedmiar|unit_mismatch|quantity_anomaly|trap
    severity      flag_severity NOT NULL,
    message       text NOT NULL,
    provenance    jsonb NOT NULL,            -- {source,doc_id,page,line_or_pos,confidence}
    axiom_id      uuid,                       -- which axiom raised it (FK added after axiom table)
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_discrepancy_tender ON discrepancy (tenant_id, tender_id, severity);

-- ---------- estimates (two variants) ----------
CREATE TABLE estimate (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    variant       estimate_variant NOT NULL,
    total_net_pln numeric(16,2),
    overhead_pct  numeric(6,3),
    profit_pct    numeric(6,3),
    params        jsonb NOT NULL DEFAULT '{}',-- editable variables (sidebar)
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, tender_id, variant)
);

CREATE TABLE estimate_line (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    estimate_id   uuid NOT NULL REFERENCES estimate(id) ON DELETE CASCADE,
    przedmiar_item_id uuid REFERENCES przedmiar_item(id),
    description   text NOT NULL,
    unit          text,
    quantity      numeric(16,4),
    -- detailed RMS (variant B); simplified unit price (variant A)
    unit_price    numeric(16,4),
    labor_pln     numeric(16,4),
    material_pln  numeric(16,4),
    equipment_pln numeric(16,4),
    line_total_pln numeric(16,2),
    provenance    jsonb,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_estline_estimate ON estimate_line (tenant_id, estimate_id);

-- ---------- owner economic engine (LOCAL ONLY — never sent to cloud LLM) ----------
CREATE TABLE rate_card (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    key           text NOT NULL,             -- material/labor/equipment key
    unit          text,
    rate_pln      numeric(16,4) NOT NULL,
    efficiency    numeric(10,4),             -- crew/equipment productivity
    source        text,                       -- 'owner_excel' | 'knr_prior' | 'market'
    valid_from    date,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, key, valid_from)
);

CREATE TABLE calibration_coeff (              -- learning loop output
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    key           text NOT NULL,
    coeff         numeric(12,6) NOT NULL,
    variance      numeric(12,6),
    version       int NOT NULL DEFAULT 1,
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------- RFQ / email-broker (the "own SQL" = tables here, not a separate server) ----------
CREATE TABLE rfq (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid REFERENCES tender(id),
    scope_desc    text NOT NULL,             -- e.g. "plac zabaw"
    status        rfq_status NOT NULL DEFAULT 'draft',
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE rfq_message (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    rfq_id        uuid NOT NULL REFERENCES rfq(id) ON DELETE CASCADE,
    direction     text NOT NULL,             -- out|in
    counterparty  text,
    subject       text,
    body          text,
    parsed_offer  jsonb,                      -- {amount_pln, validity, notes}
    message_uid   text,                       -- IMAP uid for idempotency
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_rfqmsg_rfq ON rfq_message (tenant_id, rfq_id);

-- ---------- decision engine: axioms, risk runs ----------
CREATE TABLE axiom (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    class         axiom_class NOT NULL,
    code          text NOT NULL,             -- stable identifier
    body          text NOT NULL,             -- ASP rule or Z3 constraint DSL
    description   text,
    test_ref      text,                       -- path to the test asserting this axiom
    version       int NOT NULL DEFAULT 1,
    active        boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code, version)
);
ALTER TABLE discrepancy ADD CONSTRAINT fk_discrepancy_axiom
    FOREIGN KEY (axiom_id) REFERENCES axiom(id);

CREATE TABLE risk_run (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    tender_id     uuid NOT NULL REFERENCES tender(id),
    estimate_id   uuid REFERENCES estimate(id),
    samples       int NOT NULL,
    margin_p10    numeric(8,4),
    margin_p50    numeric(8,4),
    margin_p90    numeric(8,4),
    win_prob_at_price jsonb,                  -- [{price_pln, win_prob, margin_p50}]
    drivers       jsonb,                      -- Sobol indices [{factor, S1, ST}]
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------- Module 3: resources, contracts, calendar, plans (Tier 3) ----------
CREATE TABLE resource_equipment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    type text NOT NULL, model text, reg_no text, capacity jsonb, active boolean DEFAULT true
);
CREATE TABLE employee (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    name text NOT NULL, phone text, role text, active boolean DEFAULT true
);
CREATE TABLE competency (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    employee_id uuid NOT NULL REFERENCES employee(id), skill text NOT NULL, level int
);
CREATE TABLE availability (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    employee_id uuid REFERENCES employee(id), equipment_id uuid REFERENCES resource_equipment(id),
    day date NOT NULL, available boolean NOT NULL DEFAULT true, note text
);
CREATE TABLE contract (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    tender_id uuid REFERENCES tender(id), title text NOT NULL, state text NOT NULL DEFAULT 'won',
    start_date date, end_date date, location_address text, lat numeric(9,6), lng numeric(9,6),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE calendar_event (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    contract_id uuid REFERENCES contract(id), day date NOT NULL, title text,
    equipment_ids uuid[] DEFAULT '{}', employee_ids uuid[] DEFAULT '{}'
);
CREATE TABLE daily_plan (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    contract_id uuid REFERENCES contract(id), day date NOT NULL,
    location_address text, lat numeric(9,6), lng numeric(9,6),
    photos jsonb DEFAULT '[]', drawings jsonb DEFAULT '[]',
    cautions_md text, boss_note text, status plan_status NOT NULL DEFAULT 'draft',
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE dispatch (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    daily_plan_id uuid NOT NULL REFERENCES daily_plan(id), employee_id uuid REFERENCES employee(id),
    channel text NOT NULL,                    -- mobile|whatsapp|telegram
    sent_at timestamptz, acknowledged_at timestamptz
);
CREATE TABLE field_status (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    daily_plan_id uuid REFERENCES daily_plan(id), employee_id uuid REFERENCES employee(id),
    note text, photos jsonb DEFAULT '[]', reported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mobile_device (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    employee_id uuid REFERENCES employee(id), device_token text NOT NULL UNIQUE,
    platform text, push_token text, created_at timestamptz NOT NULL DEFAULT now()
);

-- ---------- cross-cutting: approvals, agents, audit ----------
CREATE TABLE approval_request (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    action text NOT NULL,                     -- send_email|submit_docs|dispatch_plan|...
    payload jsonb NOT NULL, status approval_status NOT NULL DEFAULT 'pending',
    requested_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz, decided_by text
);
CREATE TABLE agent_run (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenant(id),
    agent text NOT NULL, status agent_status NOT NULL DEFAULT 'queued',
    input jsonb, output jsonb, state jsonb,   -- LangGraph checkpoint
    tokens_in int DEFAULT 0, tokens_out int DEFAULT 0, cost_pln numeric(12,4) DEFAULT 0,
    started_at timestamptz, finished_at timestamptz, error text
);
CREATE TABLE audit_log (                       -- append-only; no UPDATE/DELETE allowed
    id bigserial PRIMARY KEY, tenant_id uuid NOT NULL REFERENCES tenant(id),
    at timestamptz NOT NULL DEFAULT now(), actor text NOT NULL, action text NOT NULL,
    entity text, entity_id uuid, detail jsonb
);
CREATE INDEX ix_audit_tenant_at ON audit_log (tenant_id, at);
-- enforce append-only at app layer + DB trigger that raises on UPDATE/DELETE (implement in migration).
