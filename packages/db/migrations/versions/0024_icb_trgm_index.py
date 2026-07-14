"""Add pg_trgm GIN index on icb_ceny_srednie.nazwa for fast fuzzy search.

Revision ID: 0024_icb_trgm_index
Revises: 0023_password_reset_tokens
"""
from alembic import op
import sqlalchemy as sa

revision = '0024_icb_trgm_index'
down_revision = '0023_password_reset_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pg_trgm extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # GIN index for fast similarity/ILIKE search on nazwa
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_icb_nazwa_trgm
        ON icb_ceny_srednie USING GIN (nazwa gin_trgm_ops)
    """)
    # Composite index for quarter + typ_rms filters (most common query pattern)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_icb_quarter_typ
        ON icb_ceny_srednie (kwartalrok DESC, kwartalnr DESC, typ_rms)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_icb_nazwa_trgm")
    op.execute("DROP INDEX IF EXISTS idx_icb_quarter_typ")
