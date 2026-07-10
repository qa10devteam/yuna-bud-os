"""S81/S82 — Gantt v2: zarządzanie zadaniami Gantt dla przetargów."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/gantt", tags=["gantt-v2"])


@router.get("/list")
def list_gantt_projects(user: AuthUser) -> list:
    """Lista projektów Gantt dla tenanta."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """SELECT DISTINCT ON (tender_id) tender_id,
                          MIN(start_date) as start_date,
                          MAX(end_date) as end_date,
                          COUNT(*) as task_count
                   FROM gantt_tasks
                   GROUP BY tender_id
                   ORDER BY tender_id, MIN(start_date) DESC
                   LIMIT 50"""
            )
        ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/{tender_id}")
def get_gantt(tender_id: str, user: AuthUser) -> list:
    """S81 — Pobierz zadania Gantt dla przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """SELECT id, tender_id, parent_id, name, start_date, end_date,
                          progress, color, position, created_at
                   FROM gantt_tasks
                   WHERE tender_id = :tid
                   ORDER BY position, created_at"""
            ),
            {"tid": tender_id},
        ).mappings().fetchall()
    return [dict(r) for r in rows]


@router.post("/{tender_id}/tasks")
def add_gantt_task(tender_id: str, body: dict, user: AuthUser) -> dict:
    """S81 — Dodaj zadanie Gantt."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """INSERT INTO gantt_tasks
                       (id, tender_id, name, start_date, end_date, progress, color, position)
                   VALUES (gen_random_uuid(), :tender_id, :name, :start_date, :end_date,
                           :progress, :color, :position)"""
            ),
            {
                "tender_id": tender_id,
                "name": body.get("name", ""),
                "start_date": body.get("start_date"),
                "end_date": body.get("end_date"),
                "progress": body.get("progress", 0),
                "color": body.get("color", "#3b82f6"),
                "position": body.get("position", 0),
            },
        )
    return {"status": "created"}


@router.post("/{tender_id}/auto-generate")
def auto_generate_gantt(tender_id: str, user: AuthUser) -> dict:
    """S82 — Auto-generuj fazy Gantt na podstawie deadline przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        tender = conn.execute(
            text("SELECT deadline_at FROM tender WHERE id = :id"),
            {"id": tender_id},
        ).fetchone()

    if not tender or not tender.deadline_at:
        raise HTTPException(status_code=404, detail={"error": "tender_not_found"})

    from datetime import timedelta
    d = tender.deadline_at.date() if hasattr(tender.deadline_at, "date") else tender.deadline_at

    phases = [
        ("Przygotowanie", d - timedelta(days=60), d - timedelta(days=30)),
        ("Realizacja", d - timedelta(days=30), d),
        ("Odbiór", d, d + timedelta(days=14)),
    ]

    with engine.begin() as conn:
        for idx, (name, start, end) in enumerate(phases):
            conn.execute(
                text(
                    """INSERT INTO gantt_tasks
                           (id, tender_id, name, start_date, end_date, position)
                       VALUES (gen_random_uuid(), :tid, :name, :s, :e, :pos)"""
                ),
                {"tid": tender_id, "name": name, "s": start, "e": end, "pos": idx},
            )

    return {"phases_created": len(phases), "tender_id": tender_id}


@router.delete("/{tender_id}/tasks/{task_id}")
def delete_gantt_task(tender_id: str, task_id: str, user: AuthUser) -> dict:
    """Usuń zadanie Gantt."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM gantt_tasks WHERE id = :task_id AND tender_id = :tender_id"),
            {"task_id": task_id, "tender_id": tender_id},
        )
    return {"status": "deleted"}
