"""0014_tender_risk_level

Adds risk_level column to tender table. S98.
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_tender_risk_level"
down_revision = "0013_workflow_def"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tender ADD COLUMN IF NOT EXISTS risk_level TEXT DEFAULT 'unknown'")


def downgrade() -> None:
    op.execute("ALTER TABLE tender DROP COLUMN IF EXISTS risk_level")
