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
    dashboard,  # BUG FIX — dashboard endpoints
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
    from .routers import sources_health
    _optional_routers.append(('sources_health', sources_health))
except ImportError: pass
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

try:
    from .routers import scoring_config
    _optional_routers.append(('scoring_config', scoring_config))
except Exception as e:
    logging.getLogger(__name__).warning("scoring_config import error: %s", e)
try:
    from .routers import alert_config
    _optional_routers.append(('alert_config', alert_config))
except Exception as e:
    logging.getLogger(__name__).warning("alert_config import error: %s", e)
try:
    from .routers import intelligence
    _optional_routers.append(('intelligence', intelligence))
except Exception as e:
    logging.getLogger(__name__).warning("intelligence router import error: %s", e)
try:
    from .routers import kosztorys_v2
    _optional_routers.append(('kosztorys_v2', kosztorys_v2))
except Exception as e:
    logging.getLogger(__name__).warning("kosztorys_v2 router import error: %s", e)
try:
    from .routers import automations
    _optional_routers.append(('automations', automations))
except Exception as e:
    logging.getLogger(__name__).warning("automations router import error: %s", e)
from .auth import router as auth_router

# ─── Middleware helpers ────────────────────────────────────────────────────────
from .middleware.validation import validate_request
from .middleware.rate_limit import limiter
from .middleware.tenant import TenantMiddleware, install_rls_on_engine
from .middleware.csrf import CSRFMiddleware
from .middleware.error_boundary import error_boundary_handler


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

# S20/S21: Global error boundary for all unhandled exceptions
app.add_exception_handler(Exception, error_boundary_handler)

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
app.include_router(dashboard.router)  # BUG FIX — dashboard endpoints

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

if 'sources_health' in _opt_map:
    app.include_router(_opt_map['sources_health'].router)
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
    for attr in ['sub_router', 'equip_router', 'gantt_router', 'calendar_router',
                 'employees_router', 'res_equip_router', 'logistics_router', 'contracts_router']:
        if hasattr(mod, attr):
            app.include_router(getattr(mod, attr))

# F12: Scoring config
if 'scoring_config' in _opt_map:
    app.include_router(_opt_map['scoring_config'].router)

# S50 + S51 — CPV win rates + competitor win rates
try:
    from .routers import cpv_win_rates as _cpv_win_rates_mod
    app.include_router(_cpv_win_rates_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("cpv_win_rates router error: %s", _e)

# S47 — offer history import
try:
    from .routers import import_offer_history as _import_offer_history_mod
    app.include_router(_import_offer_history_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("import_offer_history router error: %s", _e)

# S54 — market share analytics
try:
    from .routers.competitor_watch import market_share_router as _market_share_router
    app.include_router(_market_share_router)
except ImportError as _e:
    logging.getLogger(__name__).warning("market_share router error: %s", _e)
# S13: Alert config UI
if 'alert_config' in _opt_map:
    app.include_router(_opt_map['alert_config'].router)

# S103-S105 — Onboarding
try:
    from .routers import onboarding as _onboarding_mod
    app.include_router(_onboarding_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("onboarding router error: %s", _e)

# S109-S110 — API v3 (webhooks + WebSocket)
try:
    from .routers.v3 import webhooks as _v3_webhooks
    from .routers.v3 import ws_tenders as _v3_ws
    app.include_router(_v3_webhooks.router)
    app.include_router(_v3_ws.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("v3 routers error: %s", _e)

# S112-S115 — Integrations
try:
    from .routers import integrations as _integrations_mod
    app.include_router(_integrations_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("integrations router error: %s", _e)

# S117 — PWA subscribe
try:
    from .routers import pwa as _pwa_mod
    app.include_router(_pwa_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("pwa router error: %s", _e)

# S118-S120 — Reports
try:
    from .routers import reports as _reports_mod
    app.include_router(_reports_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("reports router error: %s", _e)

# S121-S124 — AI Chat enhancements
try:
    from .routers import chat_ai as _chat_ai_mod
    app.include_router(_chat_ai_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("chat_ai router error: %s", _e)

# S125-S126 — Data Quality
try:
    from .routers import data_quality as _dq_mod
    app.include_router(_dq_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("data_quality router error: %s", _e)

# S127-S129 — Observability/metrics
try:
    from .routers import observability as _obs_mod
    app.include_router(_obs_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("observability router error: %s", _e)

# S132-S133 — Feature flags + A/B
try:
    from .routers import feature_flags as _ff_mod
    app.include_router(_ff_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("feature_flags router error: %s", _e)

# S135 — Kaizen Faza3 summary
try:
    from .routers import kaizen as _kaizen_mod
    app.include_router(_kaizen_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("kaizen router error: %s", _e)
