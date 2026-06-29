"""M4 — axiom DB loader.

Loads AXIOM_CORPUS into the `axiom` table (tenant-scoped).
Idempotent: uses INSERT … ON CONFLICT DO NOTHING.

Usage (CLI):
    python -m services.engine.axiom_loader <tenant_id>

Usage (library):
    from services.engine.axiom_loader import load_axioms_to_db
    load_axioms_to_db(engine, tenant_id)
"""
from __future__ import annotations

import uuid
import sqlalchemy as sa
from typing import Any

from services.engine.l1_symbolic import AXIOM_CORPUS


def load_axioms_to_db(engine: Any, tenant_id: str) -> dict[str, str]:
    """Insert axioms from AXIOM_CORPUS into DB. Returns {code: axiom_id} map.

    Idempotent via ON CONFLICT (tenant_id, code, version) DO NOTHING.
    Reads existing IDs where already present.
    """
    code_to_id: dict[str, str] = {}

    with engine.begin() as conn:
        for code, ax in AXIOM_CORPUS.items():
            # Try to get existing
            row = conn.execute(
                sa.text(
                    "SELECT id FROM axiom WHERE tenant_id = :tid AND code = :code AND version = 1"
                ),
                {"tid": tenant_id, "code": code},
            ).fetchone()

            if row:
                code_to_id[code] = str(row[0])
            else:
                new_id = str(uuid.uuid4())
                conn.execute(
                    sa.text(
                        "INSERT INTO axiom (id, tenant_id, class, code, body, description, version, active, created_at) "
                        "VALUES (:id, :tid, cast(:cls as axiom_class), :code, :body, :desc, 1, true, now()) "
                        "ON CONFLICT (tenant_id, code, version) DO NOTHING"
                    ),
                    {
                        "id": new_id,
                        "tid": tenant_id,
                        "cls": ax["class"],
                        "code": code,
                        "body": ax["body"],
                        "desc": ax.get("description", ""),
                    },
                )
                # Re-fetch in case of conflict
                row2 = conn.execute(
                    sa.text("SELECT id FROM axiom WHERE tenant_id = :tid AND code = :code AND version = 1"),
                    {"tid": tenant_id, "code": code},
                ).fetchone()
                code_to_id[code] = str(row2[0]) if row2 else new_id

    return code_to_id


if __name__ == "__main__":
    import sys
    from terra_db.session import get_engine

    if len(sys.argv) < 2:
        print("Usage: python -m services.engine.axiom_loader <tenant_id>")
        sys.exit(1)

    engine = get_engine()
    mapping = load_axioms_to_db(engine, sys.argv[1])
    for code, ax_id in mapping.items():
        print(f"  {code} → {ax_id}")
