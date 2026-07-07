"""0006 — Row Level Security policies for all tenant tables.

Revision ID: 0006_rls
Revises: 0005_phases_41_60
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0006_rls"
down_revision = "0005_phases_41_60"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helper — fetch all tables in 'public' schema that have a tenant_id column.
# We query at migration time so we never hard-code the list.
# ---------------------------------------------------------------------------

def _tenant_tables(conn) -> list[str]:
    result = conn.execute(sa.text(
        "SELECT table_name "
        "FROM information_schema.columns "
        "WHERE column_name='tenant_id' AND table_schema='public' "
        "ORDER BY table_name"
    ))
    return [row[0] for row in result]


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

HELPER_FUNCTION = """
CREATE OR REPLACE FUNCTION set_tenant_id(tid uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM set_config('app.tenant_id', tid::text, true);
END;
$$;
"""


def upgrade() -> None:
    conn = op.get_bind()
    tables = _tenant_tables(conn)

    # 1. Create helper function
    conn.execute(sa.text(HELPER_FUNCTION))

    # 2. Enable RLS + create per-table isolation policy
    for table in tables:
        conn.execute(sa.text(
            f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'
        ))
        conn.execute(sa.text(
            f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'
        ))
        # Allow superuser (postgres) bypass — FORCE RLS still applies to
        # the app user.  current_setting returns '' when not set; we treat
        # that as "no filter" so that superuser migrations continue to work.
        conn.execute(sa.text(
            f"""
            CREATE POLICY tenant_isolation ON "{table}"
              AS PERMISSIVE
              FOR ALL
              USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
                OR current_setting('app.tenant_id', true) = ''
                OR current_setting('app.tenant_id', true) IS NULL
              )
              WITH CHECK (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
                OR current_setting('app.tenant_id', true) = ''
                OR current_setting('app.tenant_id', true) IS NULL
              )
            """
        ))


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    conn = op.get_bind()
    tables = _tenant_tables(conn)

    for table in tables:
        conn.execute(sa.text(
            f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'
        ))
        conn.execute(sa.text(
            f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY'
        ))

    conn.execute(sa.text("DROP FUNCTION IF EXISTS set_tenant_id(uuid)"))
