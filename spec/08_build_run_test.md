# spec/08 — Build, run, test

## Prerequisites
Python 3.12, Node 20, Rust stable, Flutter stable (Tier 3), Docker (dev infra). Pin via `.tool-versions`.

## Dev infrastructure
`docker-compose.dev.yml` provides Postgres 16 + pgvector and (optionally) Ollama for local dev:
```bash
docker compose -f docker-compose.dev.yml up -d      # postgres+pgvector (+ollama)
cp .env.example .env                                 # fill secrets
```

## Bootstrap
```bash
# Python
uv venv && uv pip install -e services/api -e packages/db -e packages/shared   # or pip/poetry
alembic -c packages/db/alembic.ini upgrade head      # migrations match spec/01_data_model.sql
python -m services.api.seed                          # tenant + owner_profile + sample rate_card
# UI
cd apps/ui && npm ci && npm run build                # Next.js static export
# Desktop
cd apps/desktop && cargo tauri dev                   # runs shell + sidecars + UI
# Mobile (Tier 3)
cd apps/mobile && flutter pub get && flutter run
```

## Run (dev)
```bash
uvicorn services.api.main:app --host 127.0.0.1 --port 8765   # local API
ollama serve                                                 # local models (Path B)
```

## Quality gates (must pass before any milestone is "done")
```bash
ruff check . && black --check . && mypy --strict services packages
pytest -q                          # unit + contract; ZERO network (stubs/fixtures)
pytest -q -m integration           # opt-in; hits live sources/Bedrock behind flags
cd apps/ui && npm run lint && npm run typecheck && npm test
cd apps/mobile && flutter analyze && flutter test     # Tier 3
```
CI (GitHub Actions): run the zero-network suite on every PR; integration suite is manual/scheduled.

## Test strategy
- **Unit:** pure functions (scoring, calc, engine facts, parsers) with fixtures.
- **Engine golden tests:** 3 Phase-0 tenders → expected discrepancy sets; per-axiom test (`axiom.test_ref`).
- **Sum-reconciliation tests:** estimate line totals == `total_net_pln` (zero tolerance per rounding policy).
- **Contract tests:** OpenAPI shapes; side-effect endpoints return `202 + approval_id`; approval is the only
  trigger for email/dispatch/submit; each writes audit.
- **Determinism tests:** scoring + L2 (fixed seed) reproducible.
- **Guard tests:** no owner RMS data in any cloud prompt; audit log immutable; external content not executed.
- **Fixtures** under `tests/fixtures/`: recorded BZP/TED/BK notices, sample tender docs (incl. a scanned
  przedmiar), a sample `.ath`, a sample owner Excel, inbound RFQ email.

## Definition of "buildable end-to-end"
The acceptance scenario in `spec/09` (A1) runs from ingestion → analysis → engine → two-variant estimate →
go/no-go, fully offline on fixtures. Tier 2 adds RFQ + interactive edits + L2 risk; Tier 3 adds Module 3 +
Flutter dispatch. Each is gated and independently demonstrable.
