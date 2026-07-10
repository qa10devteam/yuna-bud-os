"""S14/S15 — Dashboard Materialized View migration + refresh helper."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa


revision = '0014_mv_dashboard_stats'
down_revision = ('0012_offer_result', '0013_workflow_def')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # S14: Create materialized view mv_dashboard_stats
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_stats AS
        SELECT
            tenant_id,
            count(*) AS total,
            count(*) FILTER (WHERE match_score >= 0.5) AS high_score,
            coalesce(sum(value_pln), 0) AS pipeline_value,
            max(created_at) AS last_ingest
        FROM tender
        GROUP BY tenant_id
        WITH DATA
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS mv_dashboard_stats_tenant_idx"
        " ON mv_dashboard_stats (tenant_id)"
    )

    # S17: Add site_index_built_at column to tenant if missing
    op.execute("""
        ALTER TABLE tenant ADD COLUMN IF NOT EXISTS site_index_built_at TIMESTAMPTZ
    """)

    # S36/S37: notification_preferences table
    op.execute("""
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            org_id UUID,
            email_enabled BOOLEAN NOT NULL DEFAULT true,
            inapp_enabled BOOLEAN NOT NULL DEFAULT true,
            webhook_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (user_id)
        )
    """)

    # S28: Drop content column from bzp_documents (if unused)
    op.execute("ALTER TABLE bzp_documents DROP COLUMN IF EXISTS content")


def upgrade_indexes() -> None:
    """S29: DB Indexes — run outside transaction with op.execute (CONCURRENTLY)."""
    # NOTE: CONCURRENTLY requires no active transaction; alembic runs these in a
    # separate connection without a transaction block when called via op.execute.
    pass  # indexes created directly in DB below via raw psycopg2


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_stats")
    op.execute("ALTER TABLE tenant DROP COLUMN IF EXISTS site_index_built_at")
    op.execute("DROP INDEX IF EXISTS idx_tender_match_score")
    op.execute("DROP INDEX IF EXISTS idx_tender_deadline")
    op.execute("DROP INDEX IF EXISTS idx_tender_created")
    op.execute("DROP TABLE IF EXISTS notification_preferences")
    op.execute("ALTER TABLE bzp_documents ADD COLUMN IF NOT EXISTS content TEXT")
