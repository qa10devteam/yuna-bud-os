"""0015 — merge heads: mv_dashboard_stats + tender_risk_level

BPMN merge point — łączy dwa równoległe branche migracji.
"""
from alembic import op

revision = "0015_merge"
down_revision = ("0014_mv_dashboard_stats", "0014_tender_risk_level")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
