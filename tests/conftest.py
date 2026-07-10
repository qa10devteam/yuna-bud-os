"""Shared pytest configuration for terra-os test suite."""
from __future__ import annotations

import sys
import os

# Project root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add all necessary paths at collection time (before any test imports)
for path in [
    ROOT,
    os.path.join(ROOT, "packages", "vendor"),
    os.path.join(ROOT, "packages", "shared"),
    os.path.join(ROOT, "packages", "db"),
    os.path.join(ROOT, "services", "estimator"),
    os.path.join(ROOT, "services", "api"),
]:
    if path not in sys.path:
        sys.path.insert(0, path)

# NOTE: The API uses PEP 420 namespace packages (no __init__.py) for uvicorn.
# But pytest needs __init__.py to resolve "services.api.services.api.main".
# We create them here and clean them up via a session-scoped finalizer so that
# uvicorn (started separately) is never affected.
_pkg_inits_created: list[str] = []
for _pkg_dir in [
    os.path.join(ROOT, "services"),
    os.path.join(ROOT, "services", "api"),
]:
    _init = os.path.join(_pkg_dir, "__init__.py")
    if not os.path.exists(_init):
        open(_init, "w").close()
        _pkg_inits_created.append(_init)

# services/api appended LAST — it has its own `services/` sub-package that would
# shadow terra-os/services (engine, ingestion…) if inserted at position 0.
_api_path = os.path.join(ROOT, "services", "api")
if _api_path not in sys.path:
    sys.path.append(_api_path)

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("TESTING", "1")

# DB credentials (match running API so integration tests can connect)
# Force-set these before any DB-touching imports so lru_cache(get_engine) picks them up.
os.environ["DB_HOST"] = os.getenv("DB_HOST", "127.0.0.1")
os.environ["DB_PORT"] = os.getenv("DB_PORT", "5432")
os.environ["DB_NAME"] = os.getenv("DB_NAME", "terraos")
os.environ["DB_USER"] = os.getenv("DB_USER", "terraos")
os.environ["DB_PASSWORD"] = os.getenv("DB_PASSWORD", "terra_dev_2026")
# Pin ingestion to the demo org so tender.tenant_id == demo user's org_id
os.environ["DEFAULT_TENANT_ID"] = os.getenv("DEFAULT_TENANT_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")

# Bust lru_cache on get_engine so any cached engine with wrong creds is evicted
try:
    import sys as _sys
    _api_path = os.path.join(ROOT, "services", "api")
    if _api_path not in _sys.path:
        _sys.path.append(_api_path)
    from terra_db.session import get_engine as _ge
    _ge.cache_clear()
except Exception:
    pass


# ─── Auth fixture ─────────────────────────────────────────────────────────────
import pytest


@pytest.fixture(scope="session", autouse=True)
def _cleanup_pkg_inits():
    """Remove __init__.py files created for pytest namespace resolution.

    These files are needed so pytest can import 'services.api.services.api.main',
    but they must NOT persist after the test session because they break uvicorn's
    namespace package resolution ('services.api.main').
    """
    yield
    for init_path in _pkg_inits_created:
        try:
            os.remove(init_path)
        except OSError:
            pass


@pytest.fixture(scope="session")
def demo_token() -> str:
    """JWT access token for demo@terra-os.pl — generated without DB."""
    import sys as _sys
    _api = os.path.join(ROOT, "services", "api")
    if _api not in _sys.path:
        _sys.path.append(_api)
    from services.api.services.api.auth.utils import create_access_token
    return create_access_token(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )


@pytest.fixture(scope="session")
def auth_headers(demo_token: str) -> dict:
    """Authorization headers ready to pass to httpx."""
    return {"Authorization": f"Bearer {demo_token}"}


@pytest.fixture(scope="session", autouse=True)
def _override_auth_for_tests() -> None:
    """Inject demo user via FastAPI dependency_overrides for all ASGI tests.

    This means every AsyncClient(transport=ASGITransport(app=app)) call
    will bypass JWT validation and get a logged-in demo user automatically.
    Tests that explicitly send their own token are unaffected (overrides are
    only consulted when the dependency is resolved, and the override wins).
    """
    import sys as _sys
    _api = os.path.join(ROOT, "services", "api")
    if _api not in _sys.path:
        _sys.path.append(_api)
    try:
        from services.api.services.api.main import app
        from services.api.services.api.auth.deps import (
            get_current_user,
            CurrentUser,
        )

        _demo = CurrentUser(
            user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
            email="demo@terra-os.pl",
            org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
            role="owner",
        )
        app.dependency_overrides[get_current_user] = lambda: _demo
    except Exception:
        pass  # non-ASGI test files — no-op


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the in-process rate-limiter buckets between tests.

    The middleware uses a module-level defaultdict that accumulates all
    requests across the entire pytest session.  Without this reset every
    test suite that fires >100 ASGI requests against the same org_id
    starts getting 429 responses, causing cascading failures in m9/m7/m1.
    """
    try:
        from services.api.services.api.middleware.rate_limiter import _buckets
        _buckets.clear()
    except Exception:
        pass
    yield
    try:
        from services.api.services.api.middleware.rate_limiter import _buckets
        _buckets.clear()
    except Exception:
        pass

