"""S20/S21 — Global error boundary: catches unhandled exceptions, logs + returns 500 JSON."""
from __future__ import annotations

import logging
import traceback

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def error_boundary_handler(request: Request, exc: Exception) -> JSONResponse:
    # Let HTTPException propagate normally (FastAPI handles it)
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    # Log full traceback server-side only — never expose to client
    logger.error(
        "Unhandled exception: %s %s — %s",
        request.method,
        request.url.path,
        traceback.format_exc(),
        exc_info=True,
    )
    try:
        from ..services.audit_service import log_audit  # jeśli brak — skip
        pass
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={"detail": "Wewnętrzny błąd serwera"},
    )
