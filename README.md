# Terra.OS

**System Zarządzania Robotami Ziemnymi** dla polskich firm budowlanych.

Platforma obejmuje: Zwiad (odkrycie przetargów), Kosztorysant (wycena), Silnik (engine decyzyjny), Mózg (zarządzanie placem budowy).

## Struktura monorepo

```
terra-os/
├── apps/ui/          # Next.js 16 simulation UI (demo dla klienta)
├── services/api/     # FastAPI local REST API (Python 3.12)
├── packages/db/      # SQLAlchemy 2.0 models + Alembic migrations
├── packages/shared/  # Provenance, Flag, AuditWriter, Errors
├── spec/             # Pełna specyfikacja techniczna (M0–M9)
└── tests/            # pytest (zero-network)
```

## Quick start

```bash
# Python backend
python3.12 -m pip install -e packages/shared -e packages/db -e services/api
DB_PASSWORD=xxx python3.12 -m alembic -c packages/db/alembic.ini upgrade head
uvicorn services.api.services.api.main:app --host 127.0.0.1 --port 8765

# UI (demo)
cd apps/ui && npm ci && npm run dev

# Tests
python3.12 -m pytest tests/
```

## Status

- **M0** ✅ Scaffold, DB schema (32 tables), /health, 14 tests green
- **M1–M9** 🔄 In progress per spec/09_milestones_acceptance.md

## Spec

See [SPEC.md](SPEC.md) and [spec/](spec/) for full technical specification.
