"""FastAPI application — YU-NA local API (127.0.0.1 only)."""
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

# ─── M7 Intelligence Layer routers ────────────────────────────────────────────
try:
    from .routers import semantic_search
    _optional_routers.append(('semantic_search', semantic_search))
except Exception as e:
    logging.getLogger(__name__).warning("semantic_search router: %s", e)
try:
    from .routers import mv_scoring
    _optional_routers.append(('mv_scoring', mv_scoring))
except Exception as e:
    logging.getLogger(__name__).warning("mv_scoring router: %s", e)
try:
    from .routers import agent_pipeline
    _optional_routers.append(('agent_pipeline', agent_pipeline))
except Exception as e:
    logging.getLogger(__name__).warning("agent_pipeline router: %s", e)
try:
    from .routers import scoring
    _optional_routers.append(('scoring', scoring))
except Exception as e:
    logging.getLogger(__name__).warning("scoring router: %s", e)
try:
    from .routers import olap
    _optional_routers.append(('olap', olap))
except Exception as e:
    logging.getLogger(__name__).warning("olap router: %s", e)
try:
    from .routers import forecasting
    _optional_routers.append(('forecasting', forecasting))
except Exception as e:
    logging.getLogger(__name__).warning("forecasting router: %s", e)
try:
    from .routers import proactive
    _optional_routers.append(('proactive', proactive))
except Exception as e:
    logging.getLogger(__name__).warning("proactive router: %s", e)
try:
    from .routers import multimodal
    _optional_routers.append(('multimodal', multimodal))
except Exception as e:
    logging.getLogger(__name__).warning("multimodal router: %s", e)
try:
    from .routers import scoring_v2
    _optional_routers.append(('scoring_v2', scoring_v2))
except Exception as e:
    logging.getLogger(__name__).warning("scoring_v2 router: %s", e)
try:
    from .routers import chat_v2
    _optional_routers.append(('chat_v2', chat_v2))
except Exception as e:
    logging.getLogger(__name__).warning("chat_v2 router: %s", e)
try:
    from .routers import m7_backend
    _optional_routers.append(('m7_backend', m7_backend))
except Exception as e:
    logging.getLogger(__name__).warning("m7_backend router: %s", e)
try:
    from .routers import m7_advanced
    _optional_routers.append(('m7_advanced', m7_advanced))
except Exception as e:
    logging.getLogger(__name__).warning("m7_advanced router: %s", e)
try:
    from .routers import icb_advanced
    _optional_routers.append(('icb_advanced', icb_advanced))
except Exception as e:
    logging.getLogger(__name__).warning("icb_advanced router: %s", e)

from .auth import router as auth_router

# ─── Middleware helpers ────────────────────────────────────────────────────────
from .middleware.validation import validate_request
from .middleware.rate_limit import limiter
from .middleware.rate_limiter import rate_limit_middleware
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
    title="YU-NA API",
    version="0.1.0",
    description="YU-NA — platforma decyzyjna dla wykonawców robót budowlanych (przetargi publiczne)",
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

# S34: per-user/IP sliding-window rate limiter (100 req/min)
app.middleware("http")(rate_limit_middleware)


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
                 'employees_router', 'res_equip_router', 'logistics_router', 'contracts_router',
                 'res_v2_router']:
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
    if hasattr(_chat_ai_mod, 'ai_chat_router'):
        app.include_router(_chat_ai_mod.ai_chat_router)
except ImportError as _e:
    logging.getLogger(__name__).warning("chat_ai router error: %s", _e)

# S55-S57 — Market Materials
try:
    from .routers import market_materials as _market_materials_mod
    app.include_router(_market_materials_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("market_materials router error: %s", _e)

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

try:
    from .routers import ab_testing as _ab_mod
    app.include_router(_ab_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("ab_testing router error: %s", _e)

# S135 — Kaizen Faza3 summary
try:
    from .routers import kaizen as _kaizen_mod
    app.include_router(_kaizen_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("kaizen router error: %s", _e)

# Escalation log
try:
    from .routers import escalation as _escalation_mod
    app.include_router(_escalation_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("escalation router error: %s", _e)

# RFQ v2 router (GET /api/v2/rfq)
try:
    from .routers import rfq as _rfq_mod
    if hasattr(_rfq_mod, 'router_v2'):
        app.include_router(_rfq_mod.router_v2)
except ImportError as _e:
    logging.getLogger(__name__).warning("rfq_v2 router error: %s", _e)

# S81/S82 — GANTT v2
try:
    from .routers import gantt as _gantt_mod
    app.include_router(_gantt_mod.router)
except ImportError as _e:
    logging.getLogger(__name__).warning("gantt v2 router error: %s", _e)

# ─── M7 Intelligence Layer ────────────────────────────────────────────────────
if 'semantic_search' in _opt_map:
    app.include_router(_opt_map['semantic_search'].router)
if 'mv_scoring' in _opt_map:
    app.include_router(_opt_map['mv_scoring'].router)
if 'agent_pipeline' in _opt_map:
    app.include_router(_opt_map['agent_pipeline'].router)
if 'chat_v2' in _opt_map:
    app.include_router(_opt_map['chat_v2'].router)
if 'm7_backend' in _opt_map:
    app.include_router(_opt_map['m7_backend'].router)
if 'm7_advanced' in _opt_map:
    app.include_router(_opt_map['m7_advanced'].router)
if 'icb_advanced' in _opt_map:
    app.include_router(_opt_map['icb_advanced'].router)
if 'scoring' in _opt_map:
    app.include_router(_opt_map['scoring'].router)
if 'olap' in _opt_map:
    app.include_router(_opt_map['olap'].router)
if 'forecasting' in _opt_map:
    app.include_router(_opt_map['forecasting'].router)
if 'proactive' in _opt_map:
    app.include_router(_opt_map['proactive'].router)
if 'multimodal' in _opt_map:
    app.include_router(_opt_map['multimodal'].router)
if 'scoring_v2' in _opt_map:
    app.include_router(_opt_map['scoring_v2'].router)

# ── v1 compat aliases — frontend używa /api/v1/tenders ──────────────────────
from fastapi import Request as _Request
from fastapi.responses import JSONResponse as _JSONResponse

@app.get("/api/v1/tenders", include_in_schema=False)
async def v1_tenders_list(_req: _Request):
    """Alias: przekierowuje v1 → v2 tenders list."""
    from .routers.tenders_v2 import router as _tv2
    from .auth.deps import get_current_user as _gcu
    from starlette.testclient import TestClient as _TC
    # Proste proxy — pobierz querystring i odpytaj v2
    qs = str(_req.url.query)
    target = f"/api/v2/tenders{'?' + qs if qs else ''}"
    token = _req.headers.get("authorization", "")
    import httpx as _httpx
    async with _httpx.AsyncClient(base_url="http://127.0.0.1:8765") as client:
        resp = await client.get(target, headers={"Authorization": token})
    return _JSONResponse(content=resp.json(), status_code=resp.status_code)
