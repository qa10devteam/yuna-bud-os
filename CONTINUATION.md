# Terra.OS — kontynuacja projektu (Tier 3, M7+)

## Repo
https://github.com/qa10devteam/terra-os.git
branch: main, last commit: 384f132

## Stack
- Python 3.12 system-wide (`/usr/bin/python3.12`)
- FastAPI monorepo: `services/api/`, `services/ingestion/`, `services/documents/`, `services/ai/`, `services/estimator/`, `services/engine/`
- Next.js 16 UI: `apps/ui/`
- PostgreSQL 16 lokalnie: host=127.0.0.1, port=5432, db=terraos, user=terraos
- pgvector + pgcrypto aktywne
- Wszystkie pakiety zainstalowane edytowalnie (`pip install -e`)
- clingo 5.8.0 + z3-solver + scipy 1.18.0 zainstalowane (`--break-system-packages`)

## DB password
`terraosdev2026` — przekazuj przez env `DB_PASSWORD`, nie przez terminal (Hermes redaktuje `***`)

## Uruchamianie testów
```bash
TERRA_OFFLINE=1 DB_PASSWORD=*** DB_HOST=127.0.0.1 DB_PORT=5432 DB_NAME=terraos DB_USER=terraos \
  python3.12 -m pytest tests/ -q
```
Wynik: **155/165 ✅** (M0+M1+M2+M3+M4+M5+M6)
Uwaga: 10 pre-istniejących failures w test_m1_ingest.py (IntegrityError w _clean_tenders) — nie regresja.

## Ukończone Milestones

### M0 — Scaffold (commit 84baa30) · 14 testów ✅
### M1 — Zwiad BZP (commit 1094517) · 29 testów ✅
### M2 — Documents/OCR/RAG (commit 73dd0f5) · 21 testów ✅
### M3 — Estimator MVP (commit 147554f) · 21 testów ✅ · Acceptance A1 ✅
### M4 — Decision Engine L1 (commit 001aa9f) · 29 testów ✅
- clingo + Z3, aksjoaty A001–A006, /engine/run, /rules/check
- UWAGA: integer arithmetic — PLN→grosze, m→cm

### M5 — Decision Engine L2 (commit 9e9b9b6) · 28 testów ✅
- Monte Carlo 2000 próbek, Sobol S1/ST, win_prob_at_price[]
- /risk endpoint, risk{} block w /engine/run
- scipy 1.18.0

### M6 — Email-broker + Approval gate + Chat-brain + Autofill (commit 384f132) · 23 testów ✅ · **Tier 2 DONE** · Acceptance A2 ✅
- `services/api/.../routers/rfq.py` — POST /rfq → 202, GET /rfq/{id}, POST /rfq/{id}/inbound (regex parser), GET/POST /approvals
- `services/api/.../routers/chat.py` — POST /estimates/{id}/chat SSE, regex intent parser, deterministic apply, audit_log
- POST /tenders/{id}/autofill → 202 (gated draft, never submits)
- Approval gate: JEDYNA ścieżka do send/submit → audit_log
- Acceptance A2: ingest→analyze→estimate→compare→engine(L1+L2)→RFQ→approve→inbound→parse→param_edit→autofill ✅

## Następny krok: M7 — Module 3 core (Tier 3)

### Co budować (spec/09):
**Build:** registries (equipment/employees/competency/availability/contracts),
OR-Tools logistics optimizer, plan assembly (`/plans`).

**DoD:** feasible assignment respects availability/competency; infeasible → explained.

**Acceptance T-M7:**
- fixture (2 contracts / 7 employees / limited excavators) → valid assignment
- over-constrained fixture → `engine_infeasible` with reason

### Kluczowe decyzje architektoniczne:
- Alembic migration = raw DDL (`op.execute(DDL)`) — bez `op.create_table` z SA Enum
- `_clean_tenders()` w testach musi kasować: `estimate → analysis → tender` (FK kaskada)
- `estimate.variant` = enum `doc`/`owner` (nie `A`/`B`)
- Python 3.12 przez `subprocess` z `env` dict dla DB_PASSWORD
- httpx 0.28 → `ASGITransport(app=app)` (nie `app=app` bezpośrednio)
- clingo: NO floats — integer arithmetic (grosze, cm)
- `--break-system-packages` wymagane przy pip
- Approval gate: KAŻDY side-effect przez `approval_request` → `approve` → `audit_log`

## Pliki spec
```
/home/ubuntu/terra-os/spec/
```
Spec files: 01_overview.md, 02_api_contracts.md, 03_modules.md, 09_milestones_acceptance.md …

## Vercel (apps/ui)
- Root Directory: `apps/ui` w Vercel dashboard
- Next.js 16.2.9
