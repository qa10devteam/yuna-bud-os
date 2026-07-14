"""Add password_reset_tokens table

Revision ID: 0023_password_reset_tokens
Revises: 0022_tenant_site_index
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_password_reset_tokens"
down_revision = "0022_tenant_site_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE password_reset_tokens (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token text NOT NULL UNIQUE,
            expires_at timestamptz NOT NULL,
            used_at timestamptz DEFAULT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_prt_token ON password_reset_tokens(token)")
    op.execute("CREATE INDEX idx_prt_user ON password_reset_tokens(user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_prt_user")
    op.execute("DROP INDEX IF EXISTS idx_prt_token")
    op.execute("DROP TABLE IF EXISTS password_reset_tokens")
