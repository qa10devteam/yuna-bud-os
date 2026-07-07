"""Faza 76-80: Billing — subscription table + stripe fields on organizations.

Revision ID: 0007_billing_subscription
Revises: 0005_phases_41_60
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op

revision: str = "0007_billing_subscription"
down_revision = "0006_rls"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
-- Add stripe fields to organizations (if not present)
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS stripe_customer_id     VARCHAR(255),
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS ix_org_stripe_customer ON organizations (stripe_customer_id);

-- Main subscription table (one row per org, full lifecycle)
CREATE TABLE IF NOT EXISTS subscription (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan                    VARCHAR(50)  NOT NULL DEFAULT 'free',
    status                  VARCHAR(50)  NOT NULL DEFAULT 'active',
    stripe_customer_id      VARCHAR(255),
    stripe_subscription_id  VARCHAR(255),
    stripe_price_id         VARCHAR(255),
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    trial_end               TIMESTAMPTZ,
    payment_failed          BOOLEAN NOT NULL DEFAULT FALSE,
    cancel_at_period_end    BOOLEAN NOT NULL DEFAULT FALSE,
    grace_until             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id)
);

CREATE INDEX IF NOT EXISTS idx_subscription_org_id           ON subscription (org_id);
CREATE INDEX IF NOT EXISTS idx_subscription_stripe_customer  ON subscription (stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_subscription_stripe_sub       ON subscription (stripe_subscription_id);
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS subscription CASCADE;
ALTER TABLE organizations
    DROP COLUMN IF EXISTS stripe_customer_id,
    DROP COLUMN IF EXISTS stripe_subscription_id;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
