"""S20/S21 — Global error boundary: catches unhandled exceptions, logs + returns 500 JSON."""
from __future__ import annotations

import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def error_boundary_handler(request: Request, exc: Exception) -> JSONResponse:
    tb = traceback.format_exc()
    logger.error(
        "Unhandled: %s %s — %s",
        request.method,
        request.url.path,
        tb,
    )
    try:
        from ..services.audit_service import log_audit  # jeśli brak — skip
        pass
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": str(request.url.path),
        },
    )
