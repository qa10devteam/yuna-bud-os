"""0011 — alert_failed DLQ table (Dead Letter Queue for failed alert dispatches)

BPMN Faza 1, Sprint 11
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_alert_failed_dlq"
down_revision = "0010_ingest_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_failed",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("tenant_id", sa.Text, nullable=False),
        sa.Column("alert_id", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("to_email", sa.Text, nullable=True),
        sa.Column("subject", sa.Text, nullable=True),
        sa.Column("html_body", sa.Text, nullable=True),
        sa.Column("text_body", sa.Text, nullable=True),
        sa.Column("error_msg", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="1"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text, nullable=False, server_default="'pending'"),
    )
    op.create_index("ix_alert_failed_tenant", "alert_failed", ["tenant_id"])
    op.create_index("ix_alert_failed_status_retry", "alert_failed", ["status", "next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_failed_status_retry", "alert_failed")
    op.drop_index("ix_alert_failed_tenant", "alert_failed")
    op.drop_table("alert_failed")
