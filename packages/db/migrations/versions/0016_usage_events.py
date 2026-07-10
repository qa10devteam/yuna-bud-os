"""S108 — usage_events table migration."""
from alembic import op
import sqlalchemy as sa

revision = "0016_usage_events"
down_revision = "0015_merge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id SERIAL PRIMARY KEY,
            tenant_id UUID,
            event_type TEXT,
            resource_id TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_events_tenant ON usage_events(tenant_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_events")
