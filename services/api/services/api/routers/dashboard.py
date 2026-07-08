"""
Dashboard router — statystyki ogólne dla użytkownika.

Endpoints:
    GET /api/v1/dashboard      — statystyki dla panelu głównego (v1)
    GET /api/v2/dashboard/stats — statystyki dla panelu głównego (v2)
"""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(tags=["dashboard"])


def _get_dashboard_data() -> dict:
    """Pobiera dane dashboardu z DB."""
    engine = get_engine()
    with engine.connect() as conn:
        # Łączna liczba przetargów
        total_row = conn.execute(sa.text(
            "SELECT COUNT(*) FROM tender WHERE duplicate_of IS NULL"
        )).fetchone()
        total_tenders = int(total_row[0]) if total_row else 0

        # Nowe dzisiaj
        new_today_row = conn.execute(sa.text(
            """SELECT COUNT(*) FROM tender
               WHERE DATE(created_at) = CURRENT_DATE
                 AND duplicate_of IS NULL"""
        )).fetchone()
        new_today = int(new_today_row[0]) if new_today_row else 0

        # Wysoki wynik dopasowania (match_score > 0.6)
        high_score_row = conn.execute(sa.text(
            """SELECT COUNT(*) FROM tender
               WHERE match_score > 0.6
                 AND duplicate_of IS NULL"""
        )).fetchone()
        high_score_count = int(high_score_row[0]) if high_score_row else 0

        # Podział po źródle
        source_rows = conn.execute(sa.text(
            "SELECT source, COUNT(*) FROM tender WHERE duplicate_of IS NULL GROUP BY source"
        )).fetchall()
        by_source = {row[0]: int(row[1]) for row in source_rows if row[0]}

        # Top 5 przetargów po match_score
        top_rows = conn.execute(sa.text(
            """SELECT id, title, source, value_pln, match_score, status
               FROM tender
               WHERE duplicate_of IS NULL
                 AND match_score IS NOT NULL
               ORDER BY match_score DESC
               LIMIT 5"""
        )).fetchall()
        top_tenders = [
            {
                "id": str(row[0]),
                "title": row[1],
                "source": row[2],
                "value_pln": float(row[3]) if row[3] is not None else None,
                "match_score": float(row[4]) if row[4] is not None else None,
                "status": row[5],
            }
            for row in top_rows
        ]

        # Średni wynik dopasowania
        avg_row = conn.execute(sa.text(
            "SELECT AVG(match_score) FROM tender WHERE duplicate_of IS NULL"
        )).fetchone()
        avg_score = round(float(avg_row[0]), 4) if avg_row and avg_row[0] is not None else None

    return {
        "total_tenders": total_tenders,
        "new_today": new_today,
        "high_score_count": high_score_count,
        "by_source": by_source,
        "top_tenders": top_tenders,
        "avg_score": avg_score,
    }


@router.get("/api/v1/dashboard")
def dashboard_stats_v1(user: AuthUser) -> dict:
    """Panel główny — statystyki przetargów (v1)."""
    return _get_dashboard_data()


@router.get("/api/v2/dashboard/stats")
def dashboard_stats_v2(user: AuthUser) -> dict:
    """Panel główny — statystyki przetargów (v2)."""
    return _get_dashboard_data()
