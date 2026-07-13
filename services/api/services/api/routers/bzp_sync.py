"""BZP sync management endpoints.

GET  /api/v2/bzp/sync/status    — last sync stats
POST /api/v2/bzp/sync/trigger   — manual trigger (admin)
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/api/v2/bzp/sync", tags=["bzp-sync"])


@router.get("/status")
def get_sync_status() -> dict[str, Any]:
    """Get last BZP auto-sync status."""
    try:
        from services.agents.bzp_sync import get_sync_status
        return get_sync_status()
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/trigger")
async def trigger_sync(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Manually trigger BZP sync (runs in background)."""
    try:
        from services.agents.bzp_sync import sync_bzp_batch
        background_tasks.add_task(sync_bzp_batch, 5)
        return {"status": "triggered", "pages": 5}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
