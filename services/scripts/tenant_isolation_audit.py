#!/usr/bin/env python3
"""S104 — Tenant Isolation Audit: sprawdza tabele z tenant_id pod kątem NULL."""
from __future__ import annotations

import os
import sys
import sqlalchemy as sa

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://terraos:terra_dev_2026@127.0.0.1:5432/terraos?sslmode=disable&gssencmode=disable",
)


def run_audit() -> list[dict]:
    engine = sa.create_engine(DB_URL)
    findings = []
    with engine.connect() as conn:
        # Get all tables with a tenant_id column
        tables = conn.execute(
            sa.text(
                """
                SELECT table_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND column_name = 'tenant_id'
                ORDER BY table_name
                """
            )
        ).fetchall()

        for (table,) in tables:
            try:
                row = conn.execute(
                    sa.text(f'SELECT count(*) FROM "{table}" WHERE tenant_id IS NULL')
                ).scalar()
                findings.append({"table": table, "null_tenant_id_count": row})
            except Exception as e:
                findings.append({"table": table, "error": str(e)})

    return findings


def main() -> None:
    findings = run_audit()

    print("# Tenant Isolation Audit\n")
    print(f"{'Table':<45} {'NULL tenant_id':>15}")
    print("-" * 62)
    for f in findings:
        if "error" in f:
            print(f"{f['table']:<45} ERROR: {f['error']}")
        else:
            flag = " ⚠️  ISSUE" if f["null_tenant_id_count"] > 0 else ""
            print(f"{f['table']:<45} {f['null_tenant_id_count']:>15}{flag}")

    issues = [f for f in findings if f.get("null_tenant_id_count", 0) > 0]
    print(f"\nTotal tables checked: {len(findings)}")
    print(f"Tables with NULL tenant_id: {len(issues)}")
    return findings


if __name__ == "__main__":
    main()
