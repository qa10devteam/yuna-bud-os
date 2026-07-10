"""0012_workflow_definition

Revision ID: 0012_workflow_def
Revises: 0011_alert_failed_dlq
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0013_workflow_def"
down_revision = "0012_offer_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_definition (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            name TEXT NOT NULL,
            definition JSONB NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_def_tenant ON workflow_definition (tenant_id)")


def downgrade() -> None:
    op.drop_index("ix_workflow_def_tenant", "workflow_definition")
    op.drop_table("workflow_definition")
