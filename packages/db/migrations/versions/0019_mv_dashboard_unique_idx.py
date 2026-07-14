"""0019 — Fix mv_dashboard_stats: recreate with tenant_id + unique index (P0 fix).

Revision: 0019_mv_dashboard_unique_idx

The live mv_dashboard_stats was recreated as a global aggregate (no tenant_id)
at some point, overwriting migration 0014's per-tenant version.
REFRESH CONCURRENTLY requires a unique index, which requires tenant_id.

This migration:
1. DROPs the current MV (global aggregate, no PK column)
2. RECREATEs it as per-tenant aggregate (matching 0014 intent)
3. Adds the required unique index ON (tenant_id) for CONCURRENT refresh
"""
from __future__ import annotations
from alembic import op


revision = '0019_mv_dashboard_unique_idx'
down_revision = '0018_m7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Drop the broken global-aggregate MV
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_stats")

    # Step 2: Recreate as per-tenant aggregate (original 0014 intent)
    op.execute("""
        CREATE MATERIALIZED VIEW mv_dashboard_stats AS
        SELECT
            tenant_id,
            count(*)                                           AS total,
            count(*) FILTER (WHERE match_score >= 0.5)         AS high_score,
            coalesce(sum(value_pln), 0)                        AS pipeline_value,
            max(created_at)                                    AS last_ingest
        FROM tender
        GROUP BY tenant_id
        WITH DATA
    """)

    # Step 3: Add unique index — required for REFRESH CONCURRENTLY
    # NOTE: Cannot use CONCURRENTLY inside Alembic transaction context.
    # Standard CREATE UNIQUE INDEX is safe here (MV just created, no readers yet).
    op.execute(
        "CREATE UNIQUE INDEX mv_dashboard_stats_tenant_idx "
        "ON mv_dashboard_stats (tenant_id)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_stats")
    # Restore global aggregate (pre-fix state)
    op.execute("""
        CREATE MATERIALIZED VIEW mv_dashboard_stats AS
        SELECT
            count(*) FILTER (WHERE duplicate_of IS NULL) AS total_active,
            count(*) FILTER (WHERE duplicate_of IS NULL AND date(created_at) = CURRENT_DATE) AS new_today,
            coalesce(sum(value_pln) FILTER (
                WHERE duplicate_of IS NULL
                  AND status NOT IN ('archived', 'decided_nogo')
            ), 0) AS pipeline_value,
            count(DISTINCT buyer) FILTER (WHERE duplicate_of IS NULL AND buyer IS NOT NULL) AS unique_buyers
        FROM tender
        WITH DATA
    """)
