"""Add missing columns: offers.source, offers.stage, notifications.priority.

Revision ID: 0025_missing_columns
Revises: 0024_icb_trgm_index
"""
from alembic import op
import sqlalchemy as sa

revision = '0025_missing_columns'
down_revision = '0024_icb_trgm_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add offers.source if missing
    op.execute("""
        ALTER TABLE offers
        ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'manual'
    """)

    # Add offers.stage if missing
    op.execute("""
        ALTER TABLE offers
        ADD COLUMN IF NOT EXISTS stage VARCHAR(50) DEFAULT 'draft'
    """)

    # Add notifications.priority if missing
    op.execute("""
        ALTER TABLE notifications
        ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal'
    """)

    # Add notifications.is_read if missing (some code uses is_read vs read)
    op.execute("""
        ALTER TABLE notifications
        ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE offers DROP COLUMN IF EXISTS source")
    op.execute("ALTER TABLE offers DROP COLUMN IF EXISTS stage")
    op.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS priority")
    op.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS is_read")
