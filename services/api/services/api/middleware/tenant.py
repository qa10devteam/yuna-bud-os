"""Tenant middleware — injects app.tenant_id into PostgreSQL session for RLS.

This middleware looks for ``request.state.tenant_id`` (set by auth
dependencies) and issues ``SET LOCAL app.tenant_id = '<tid>'`` at the
start of each database connection used during the request so that
PostgreSQL Row-Level Security policies can filter rows automatically.

Usage — register **after** auth middleware in main.py::

    from .middleware.tenant import TenantMiddleware
    app.add_middleware(TenantMiddleware)

The middleware itself does NOT execute SQL; instead it registers a
SQLAlchemy *checkout* event listener on the shared engine so that every
connection handed out from the pool during the request lifetime carries
the correct tenant context.
"""
from __future__ import annotations

import contextvars
from typing import Any

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Connection
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ContextVar holds the tenant_id for the current async task / thread.
# It is reset to None on every request so stale values never leak.
_current_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_tenant_id", default=None
)


def set_tenant_context(conn: Any, tenant_id: str) -> None:
    """Directly set app.tenant_id on an already-open SQLAlchemy connection.

    Use this helper inside route handlers that receive a ``db: Session``
    dependency — call it **before** the first query::

        def my_route(tenant_id: TenantDep, db: Session = Depends(get_db)):
            set_tenant_context(db.connection(), tenant_id)
            ...
    """
    conn.execute(sa.text("SELECT set_tenant_id(:tid)"), {"tid": tenant_id})


# ---------------------------------------------------------------------------
# Engine-level event: automatically SET LOCAL app.tenant_id on every
# connection checkout while a tenant context is active.
# ---------------------------------------------------------------------------

def _install_rls_listener(engine: sa.engine.Engine) -> None:
    """Register a checkout listener on *engine* (idempotent)."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, connection_record):  # noqa: ARG001
        # Nothing to do at connect-time; we act at checkout.
        pass

    @event.listens_for(engine, "checkout")
    def _on_checkout(dbapi_conn, connection_record, connection_proxy):  # noqa: ARG001
        tid = _current_tenant_id.get()
        if tid:
            cursor = dbapi_conn.cursor()
            # Use SET LOCAL so the setting is transaction-scoped and resets
            # automatically when the connection is returned to the pool.
            cursor.execute(f"SELECT set_config('app.tenant_id', %s, true)", (str(tid),))
            cursor.close()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class TenantMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware that propagates tenant context to DB.

    Flow:
    1. Reads ``request.state.tenant_id`` (UUID string or None).
       Auth dependencies (``auth/deps.py`` → ``get_tenant_id``) should set
       this on ``request.state`` **before** this middleware fires, i.e. it
       must be placed *inside* (lower stack than) any auth middleware.
       Because FastAPI route-level dependencies run after middleware, the
       simpler approach is to use the ``set_tenant_context`` helper inside
       each route that touches the DB, or to call the helper inside the
       ``get_db`` dependency.  Both patterns are shown below.
    2. Sets the ``_current_tenant_id`` ContextVar for the duration of the
       request so that the engine checkout listener picks it up.
    3. Resets the ContextVar after the response is sent (cleanup).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Auth dependencies run inside FastAPI — by the time this middleware
        # fires the dependencies haven't executed yet.  We therefore rely on
        # the ContextVar being set by get_db / route-level logic.
        # If a caller already pre-set request.state.tenant_id (e.g. via a
        # custom auth middleware that runs before this one), honour it.
        tenant_id: str | None = getattr(request.state, "tenant_id", None)

        token = _current_tenant_id.set(tenant_id)  # may be None for public routes
        try:
            response = await call_next(request)
        finally:
            _current_tenant_id.reset(token)

        return response


# ---------------------------------------------------------------------------
# Convenience: get_db dependency that sets tenant context on the session
# ---------------------------------------------------------------------------

def make_get_db_with_tenant(SessionLocal):
    """
    Factory that wraps an existing ``SessionLocal`` with tenant injection.

    Example::

        from terra_db.session import get_engine, get_session
        from .middleware.tenant import make_get_db_with_tenant, install_rls_on_engine

        install_rls_on_engine(get_engine())
        get_db = make_get_db_with_tenant(get_session())

        def my_route(db = Depends(get_db), tenant_id: TenantDep = ...):
            ...
    """
    def get_db():
        db = SessionLocal()
        try:
            tid = _current_tenant_id.get()
            if tid:
                db.execute(sa.text("SELECT set_tenant_id(:tid)"), {"tid": tid})
            yield db
        finally:
            db.close()

    return get_db


def install_rls_on_engine(engine: sa.engine.Engine) -> None:
    """Public entry-point — call once at app startup to attach RLS listener."""
    _install_rls_listener(engine)
