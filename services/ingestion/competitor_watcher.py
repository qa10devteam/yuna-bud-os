"""S52/S53 — Competitor Watcher background job.

Checks competitor_watch table and notifies on new bzp_results wins.
Also adds last_checked_at column to competitor_watch if missing.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def run_competitor_watch(engine: Engine, tenant_id: str | None = None) -> int:
    """Check for new competitor wins and create notifications.

    Args:
        engine: SQLAlchemy engine
        tenant_id: optional filter; if None, processes all tenants

    Returns:
        Number of notifications created
    """
    notifications_created = 0

    with engine.begin() as conn:
        # Ensure last_checked_at column exists
        try:
            conn.execute(
                text("""
                    ALTER TABLE competitor_watch
                    ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ;
                """)
            )
        except Exception:
            pass  # column likely exists

        query = """
            SELECT id, tenant_id, competitor_nip, competitor_name, last_checked_at, notify_on_win
            FROM competitor_watch
            WHERE notify_on_win = true
        """
        params: dict = {}
        if tenant_id:
            query += " AND tenant_id = :tenant_id"
            params["tenant_id"] = tenant_id

        watches = conn.execute(text(query), params).fetchall()

        for watch in watches:
            watch_id, w_tenant, nip, name, last_checked, notify = (
                watch[0], watch[1], watch[2], watch[3], watch[4], watch[5]
            )

            # Find new wins
            result_query = """
                SELECT id, notice_number, buyer_name, awarded_value, awarded_date, cpv_main
                FROM bzp_results
                WHERE contractor_nip = :nip
            """
            result_params: dict = {"nip": nip}

            if last_checked:
                result_query += " AND created_at > :last_checked"
                result_params["last_checked"] = last_checked

            result_query += " ORDER BY awarded_date DESC LIMIT 20"
            wins = conn.execute(text(result_query), result_params).fetchall()

            for win in wins:
                win_id, notice_no, buyer, value, date, cpv = (
                    win[0], win[1], win[2], win[3], win[4], win[5]
                )
                title = f"Rywal wygrał przetarg: {name or nip}"
                body = (
                    f"Firma {name or nip} (NIP: {nip}) wygrała przetarg "
                    f"({notice_no}) u zamawiającego {buyer or 'nieznany'}"
                    f" na kwotę {value or '?'} PLN."
                )
                try:
                    conn.execute(
                        text("""
                            INSERT INTO notifications
                                (id, tenant_id, type, title, body, metadata, created_at)
                            VALUES
                                (:id, :tenant_id, 'competitor_win', :title, :body,
                                 :metadata::jsonb, now())
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "tenant_id": str(w_tenant),
                            "title": title,
                            "body": body,
                            "metadata": f'{{"nip":"{nip}","bzp_result_id":"{win_id}",'
                                        f'"cpv":"{cpv or ""}","value":{float(value or 0)}}}',
                        },
                    )
                    notifications_created += 1
                except Exception as e:
                    logger.warning("Error inserting competitor notification: %s", e)

            # Update last_checked_at
            conn.execute(
                text("""
                    UPDATE competitor_watch
                    SET last_checked_at = now()
                    WHERE id = :id
                """),
                {"id": str(watch_id)},
            )

    logger.info("Competitor watch: created %d notifications", notifications_created)
    return notifications_created
