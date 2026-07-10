"""S4 — Performance indexes + buyer_name alias column.

S4-2: composite index tender(tenant_id, match_score DESC, duplicate_of)
S4-3: composite index tender(tenant_id, created_at DESC)  [already partial — ensure]
S4-5: buyer_name generated column as alias for buyer (for FE compat)
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_perf_indexes"
down_revision = "0016_usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # S4-2: top-N query index (match_score DESC, hide duplicates)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tender_match_score_dup
        ON tender (tenant_id, match_score DESC, duplicate_of)
        WHERE duplicate_of IS NULL
    """)

    # S4-3: new_today / created_at scan (compound with tenant_id)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tender_tenant_created
        ON tender (tenant_id, created_at DESC)
    """)

    # S4-5: buyer_name — add column as copy of buyer for FE compatibility
    # Use generated column if PG >= 12, else plain nullable with trigger
    # Simple approach: add nullable text column, backfill, keep in sync via trigger
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'tender' AND column_name = 'buyer_name'
            ) THEN
                ALTER TABLE tender ADD COLUMN buyer_name text
                    GENERATED ALWAYS AS (buyer) STORED;
            END IF;
        END;
        $$
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tender_match_score_dup")
    op.execute("DROP INDEX IF EXISTS idx_tender_tenant_created")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'tender' AND column_name = 'buyer_name'
            ) THEN
                ALTER TABLE tender DROP COLUMN buyer_name;
            END IF;
        END;
        $$
    """)
