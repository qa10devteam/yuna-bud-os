"""0012 — offer_result table for win/loss history tracking.

BPMN Faza 2, Sprint S46
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_offer_result"
down_revision = "0011_alert_failed_dlq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS offer_result (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id        UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            tender_id        UUID REFERENCES tender(id) ON DELETE SET NULL,
            status           TEXT NOT NULL DEFAULT 'submitted'
                             CHECK (status IN ('won','lost','cancelled','withdrawn','submitted')),
            bid_value_pln    NUMERIC(18,2),
            final_value_pln  NUMERIC(18,2),
            submitted_at     TIMESTAMPTZ,
            decided_at       TIMESTAMPTZ,
            competitor_name  TEXT,
            notes            TEXT,
            notice_number    TEXT,
            cpv_code         TEXT,
            nuts_code        TEXT,
            match_score      NUMERIC(5,4),
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_offer_result_tenant
            ON offer_result (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_offer_result_tender
            ON offer_result (tender_id);
        CREATE INDEX IF NOT EXISTS ix_offer_result_status
            ON offer_result (tenant_id, status);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS offer_result CASCADE;")
