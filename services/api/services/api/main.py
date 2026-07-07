"""FastAPI application — Terra.OS local API (127.0.0.1 only)."""
from __future__ import annotations

import os
import sys
import logging
import json
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

# ─── Structured JSON logging (Task 114) ───────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects for Loki/structured sinks."""
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "ts": self.formatTime(record),
        })

_root_logger = logging.getLogger()
if _root_logger.handlers:
    _root_logger.handlers[0].setFormatter(JSONFormatter())
else:
    _handler = logging.StreamHandler()
    _handler.setFormatter(JSONFormatter())
    _root_logger.addHandler(_handler)
    _root_logger.setLevel(logging.INFO)

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from terra_shared.errors import TerraError

# ─── Routers ───────────────────────────────────────────────────────────────────
from .routers import (
    health, zwiad, documents, estimator, engine,
    rfq, chat, module3, system, export, bzp, market_data,
    monitoring, gdpr, api_keys, billing, demo,
    tenders_v2, estimates_v2, decisions_v2, documents_upload, bzp_v2,
    notifications, search, audit, analytics,
    benchmark, advanced_analytics, analytics_v2,
    organizations,
    offers,  # Faza 7 — Oferty
)

# Faza 3 — nowe routery analytics/intelligence
try:
    from .routers import tender_alerts
    from .routers import tender_bookmarks
    from .routers import competitor_watch
    from .routers import buyer_crm
    from .routers import market_intelligence
    _phase3_routers = [tender_alerts, tender_bookmarks, competitor_watch, buyer_crm, market_intelligence]
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning("Phase 3 routers import error: %s", e)
    _phase3_routers = []

# Fazy 41-60 — optional routers (graceful import)
_optional_routers = []
try:
    from .routers import bzp_documents
    _optional_routers.append(('bzp_documents', bzp_documents))
except ImportError: pass
try:
    from .routers import ted_integration
    _optional_routers.append(('ted_integration', ted_integration))
except ImportError: pass
try:
    from .routers import gus_bdl
    _optional_routers.append(('gus_bdl', gus_bdl))
except ImportError: pass
try:
    from .routers import krs_verify
    _optional_routers.append(('krs_verify', krs_verify))
except ImportError: pass
try:
    from .routers import excel_import
    _optional_routers.append(('excel_import', excel_import))
except ImportError: pass
try:
    from .routers import kosztorys
    _optional_routers.append(('kosztorys', kosztorys))
except ImportError: pass
try:
    from .routers import comments
    _optional_routers.append(('comments', comments))
except ImportError: pass
try:
    from .routers import email_webhooks
    _optional_routers.append(('email_webhooks', email_webhooks))
except ImportError: pass
try:
    from .routers import sse_mcp_chat
    _optional_routers.append(('sse_mcp_chat', sse_mcp_chat))
except ImportError: pass
try:
    from .routers import resources
    _optional_routers.append(('resources', resources))
except ImportError: pass
from .auth import router as auth_router

# ─── Middleware helpers ────────────────────────────────────────────────────────
from .middleware.validation import validate_request
from .middleware.rate_limit import limiter
from .middleware.tenant import TenantMiddleware, install_rls_on_engine
from .middleware.csrf import CSRFMiddleware


# ─── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Faza 86: Apply recommended DB indexes at startup
    try:
        from .performance import apply_recommended_indexes
        apply_recommended_indexes()
    except Exception:
        pass
    # Faza RLS: Install tenant RLS checkout listener on engine
    try:
        from terra_db.session import get_engine
        install_rls_on_engine(get_engine())
    except Exception:
        pass
    yield


# ─── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Terra.OS API",
    version="0.1.0",
    description="Terra.OS — platforma decyzyjna dla wykonawców robót budowlanych (przetargi publiczne)",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT", "dev") == "dev" else None,
    redoc_url=None,
)

# ─── Prometheus metrics (Task 112) ────────────────────────────────────────────
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
except ImportError:
    pass  # prometheus_fastapi_instrumentator not installed — skip

# Attach slowapi limiter state to app
app.state.limiter = limiter


# ─── Faza 64: Security Headers Middleware ──────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# ─── Faza 67: Request Counter Middleware ───────────────────────────────────────

class RequestCounterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from .routers.monitoring import increment_request_count
        increment_request_count()
        response = await call_next(request)
        return response


# ─── Register middleware (order matters: outer → inner) ────────────────────────

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RequestCounterMiddleware)
app.add_middleware(TenantMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Faza 62: body size validation (functional middleware)
app.middleware("http")(validate_request)


# ─── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(TerraError)
async def terra_error_handler(request: Request, exc: TerraError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )

# slowapi rate limit exceeded handler
try:
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except ImportError:
    pass


# ─── Routers ───────────────────────────────────────────────────────────────────

# Faza 1 — Core routers
app.include_router(health.router)
app.include_router(auth_router)
app.include_router(zwiad.router)
app.include_router(documents.router)
app.include_router(estimator.router)
app.include_router(engine.router)
app.include_router(rfq.router)
app.include_router(chat.router)
app.include_router(module3.router)
app.include_router(system.router)
app.include_router(export.router)
app.include_router(offers.router)   # Faza 7 — Oferty
app.include_router(bzp.router)
app.include_router(market_data.router)

# Fazy 63-81 — Advanced routers (other agent)
for _r in _phase3_routers:
    app.include_router(_r.router)

app.include_router(monitoring.router)
app.include_router(gdpr.router)
app.include_router(api_keys.router)
app.include_router(billing.router)
app.include_router(demo.router)
app.include_router(organizations.router)

# Fazy 2-40 — This agent's routers
app.include_router(tenders_v2.router)
app.include_router(estimates_v2.router)
app.include_router(decisions_v2.router)
app.include_router(documents_upload.router)
app.include_router(bzp_v2.router)
app.include_router(notifications.router)
app.include_router(search.router)
app.include_router(audit.router)
app.include_router(analytics.router)
app.include_router(analytics_v2.router)
app.include_router(analytics_v2.ai_router)
app.include_router(benchmark.router)
app.include_router(advanced_analytics.router)

# Fazy 41-60 — optional routers registered if available
_opt_map = {name: mod for name, mod in _optional_routers}

if 'bzp_documents' in _opt_map:
    app.include_router(_opt_map['bzp_documents'].router)
if 'ted_integration' in _opt_map:
    app.include_router(_opt_map['ted_integration'].router)
if 'gus_bdl' in _opt_map:
    app.include_router(_opt_map['gus_bdl'].router)
if 'krs_verify' in _opt_map:
    app.include_router(_opt_map['krs_verify'].router)
if 'excel_import' in _opt_map:
    app.include_router(_opt_map['excel_import'].router)
if 'kosztorys' in _opt_map:
    app.include_router(_opt_map['kosztorys'].router)
if 'comments' in _opt_map:
    app.include_router(_opt_map['comments'].router)
if 'email_webhooks' in _opt_map:
    mod = _opt_map['email_webhooks']
    app.include_router(mod.router)
    if hasattr(mod, 'webhook_router'):
        app.include_router(mod.webhook_router)
if 'sse_mcp_chat' in _opt_map:
    mod = _opt_map['sse_mcp_chat']
    for attr in ['sse_router', 'mcp_router', 'chat_v2_router', 'playground_router']:
        if hasattr(mod, attr):
            app.include_router(getattr(mod, attr))
if 'resources' in _opt_map:
    mod = _opt_map['resources']
    for attr in ['sub_router', 'equip_router', 'gantt_router', 'calendar_router']:
        if hasattr(mod, attr):
            app.include_router(getattr(mod, attr))
