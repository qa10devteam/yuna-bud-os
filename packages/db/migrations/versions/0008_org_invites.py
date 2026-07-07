"""Phase 2: org_invites table + settings_json default columns.

Revision ID: 0008_org_invites
Revises: 0007_billing_subscription
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "0008_org_invites"
down_revision = "0007_billing_subscription"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Upewnij sie ze organizations ma settings jako JSONB z domyslna wartoscia
    op.execute("""
        ALTER TABLE organizations
        ALTER COLUMN settings SET DEFAULT '{}'::jsonb
    """)

    # 2. Tabela zaproszen
    op.execute("""
        CREATE TABLE IF NOT EXISTS org_invites (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id       uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            invited_by   uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            email        text NOT NULL,
            role         user_role NOT NULL DEFAULT 'estimator',
            token        text NOT NULL UNIQUE,
            accepted_at  timestamptz,
            expires_at   timestamptz NOT NULL DEFAULT (now() + interval '7 days'),
            created_at   timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_org_invites_token ON org_invites(token)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_org_invites_org ON org_invites(org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_org_invites_email ON org_invites(email)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS org_invites CASCADE")
