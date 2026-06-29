# CHANGELOG.md — Terra.OS

## [M9] — 2026-06-29 — Orchestration, hardening, packaging — **Tier 3 DONE**
### Added
- LangGraph supervisor pipeline: ingest→analyze→engine→estimate→decide→contract→optimize→plan→dispatch
- Learning loop: `POST /contracts/{id}/close` — aktualizacja `calibration_coeff` po zamknięciu kontraktu
- `/pipeline/run` — wyzwolenie pełnego pipeline'u (async agent_run)
- `/agents/{run_id}` + pause/resume/cancel — observability agentów
- `/system/backup/run` + `/system/backup/status` — pg_dump backup/DR
- `/audit` — read-only paginated audit_log
- `services/tier_flags.py` — TIER=1/2/3 feature flags (`is_enabled`, `require_tier`)
- `docs/RODO_PRACOWNICY.md` — klauzula informacyjna art. 13 RODO
- `docs/AI_LITERACY.md` — dokument AI-Literacy (AI Act art. 50)
- `docs/ART50_DISCLOSURE.md` — oświadczenie dostawcy
- `DECISIONS.md` — 12 kluczowych decyzji architektonicznych
- Acceptance A3: full Tier 3 end-to-end test

### Tests
- 31 nowych testów M9
- Łącznie: **217 passed**

---

## [M7] — 2026-06-29 — Logistics + Module 3 core
### Added
- OR-Tools CP-SAT optimizer (`services/logistics/`)
- Registries: equipment, employees, competency, availability, contracts
- Plans CRUD + gated dispatch
- Mobile endpoints: device register, plans fetch, field status
- 31 testów, Acceptance T-M7 ✅

---

## [M6] — 2026-06-29 — Email-broker + Approval gate + Chat-brain + Autofill
### Added
- RFQ agent (gated send, IMAP parse fixture, idempotent inbound)
- Approval gate: GET/POST /approvals + approve/reject + audit_log
- Chat-brain SSE: regex intent → deterministic param edit → sum reconciled
- Autofill: POST /tenders/{id}/autofill → 202 (never submits)
- 23 testów, Acceptance A2 ✅ — **Tier 2 DONE**

---

## [M5] — 2026-06-29 — Decision Engine L2 (Monte Carlo + Sobol)
### Added
- Monte Carlo sampler (2000 próbek, seed=42)
- Sobol S1/ST sensitivity (Saltelli estimator)
- win_prob_at_price[], /risk endpoint
- L1+L2 razem w /engine/run
- 28 testów ✅

---

## [M4] — 2026-06-29 — Decision Engine L1 (Clingo + Z3)
### Added
- Clingo symbolic engine, aksjoaty A001–A006
- /engine/run, /rules/check
- Integer arithmetic (grosze, cm)
- 29 testów ✅

---

## [M3] — 2026-06-29 — Estimator MVP
### Added
- Kosztorys variant doc/owner, RateCard, kp/zysk/robocizna
- verify_sum_reconciliation
- POST /tenders/{id}/estimate, GET compare
- PATCH /estimates/{id}/params
- 21 testów, Acceptance A1 ✅

---

## [M2] — 2026-06-29 — Documents / OCR / RAG
### Added
- OCR pipeline, document_chunk, pgvector embeddings
- Analiza przedmiaru, red_flags
- POST /tenders/{id}/analyze
- 21 testów ✅

---

## [M1] — 2026-06-29 — Zwiad BZP
### Added
- BZP scraper (offline fixture), CPV/geo matching
- POST /ingest/run, GET /tenders
- 29 testów ✅

---

## [M0] — 2026-06-29 — Scaffold
### Added
- FastAPI monorepo, PostgreSQL schema, Alembic migrations
- terra_db, terra_shared, packages/
- 14 testów ✅
