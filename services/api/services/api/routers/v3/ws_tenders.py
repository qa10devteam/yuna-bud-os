"""S110 — WebSocket tender feed: /api/v3/ws/tenders/{tenant_id}"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ws-v3"])


@router.websocket("/api/v3/ws/tenders/{tenant_id}")
async def ws_tender_feed(ws: WebSocket, tenant_id: str) -> None:
    """S110 — WebSocket feed przetargów dla danego tenanta.

    Wysyła heartbeat co 30s. Po ingest pipeline emituje zdarzenia.
    """
    await ws.accept()
    logger.info("WS connected: tenant=%s", tenant_id)
    try:
        while True:
            await asyncio.sleep(30)
            await ws.send_json({
                "type": "heartbeat",
                "tenant_id": tenant_id,
                "ts": datetime.now().isoformat(),
            })
    except WebSocketDisconnect:
        logger.info("WS disconnected: tenant=%s", tenant_id)
    except Exception as e:
        logger.warning("WS error tenant=%s: %s", tenant_id, e)
