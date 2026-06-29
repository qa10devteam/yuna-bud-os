# spec/09 — Milestones & acceptance (the build plan)

Build sequentially. Each milestone has a **Definition of Done (DoD)** and **acceptance tests**. Do not pass a
gate until its tests are green and quality gates (spec/08) pass. Record assumptions in `DECISIONS.md`.

Tier mapping: **M0–M3 = Tier 1 (Fundament, 65k)** · **M4–M6 = Tier 2 (Silnik, 180k)** · **M7–M9 = Tier 3 (Mózg, 560k)**.
Phase 0 (spike) precedes M4 and produces: solver choice confirmation, the class-C earthworks axiom corpus
(validated on 3 real tenders), and a calibration test on historical owner data.

---

### M0 — Scaffold & infra
**Build:** monorepo layout (SPEC §3), `docker-compose.dev.yml` (Postgres+pgvector, Ollama), `.env.example`,
Alembic migrations matching `spec/01_data_model.sql`, `seed`, CI (zero-network), lint/type config, shared
packages (provenance, flag, audit, errors), LLM router skeleton with `StubClient`.
**DoD:** `pytest` green (empty/scaffold tests), migrations up/down clean, `/health` returns db ok.
**Acceptance:** `alembic upgrade head` then `downgrade base` round-trips; CI passes offline.

### M1 — Ingestion + matching (Tier 1)
**Build:** connectors `bzp/ted/bk` (fixtures), normalize, CPV/geo filter, deterministic scorer + local-LLM
relevance sub-pass, `/ingest/run`, `/tenders`, `/tenders/{id}`.
**DoD:** ingestion idempotent; filter correct; list ordered by `match_score`.
**Acceptance T-M1:** load fixture notices → expected tenders upserted; out-of-CPV/geo dropped; re-run → no
dupes; `/tenders` order correct.

### M2 — Documents + analysis (Tier 1)
**Build:** document fetch/classify/OCR(Gemma)/parse_przedmiar/chunk+embed; Agentic RAG summary + cited
red-flags; tracker agent; `/tenders/{id}/analyze`, `/analysis`, `/watch`.
**DoD:** parsed przedmiar items with page provenance; every red-flag has provenance; low-confidence flagged.
**Acceptance T-M2:** scanned-przedmiar fixture → ≥N items with units/quantities/page; onerous-clause fixture
→ cited red-flag; no provenance-less claim.

### M3 — Estimator MVP → **Tier 1 (Fundament) DONE**
**Build:** variant A (doc, simplified calc) + variant B (owner Excel import → rate_card → detailed RMS),
`compare`, basic chat edits; owner data stays local.
**DoD:** both variants compute; line totals reconcile exactly; compare delta correct; no owner RMS in cloud.
**Acceptance A1 (Tier 1 end-to-end, offline):**
`ingest → /tenders → analyze → two-variant estimate → compare` runs on fixtures and a human can reach a
go/no-go view. Sum-reconciliation + no-egress-of-rates tests pass.

### M4 — Decision engine L1 (Tier 2)
**Build:** `engine/l1_symbolic` (clingo + Z3), facts builder, axiom tables + loader, discrepancy emission with
provenance + `axiom_id`; `/engine/run`, `/rules/check`. Earthworks class-C corpus from Phase 0.
**DoD:** golden fixtures produce expected discrepancies; each axiom has a passing test; missing fact → flag.
**Acceptance T-M4:** broken-przedmiar fixture (missing dewatering, mass-balance off, sum mismatch) → exact
flags with correct provenance; a clean fixture → feasible, no false positives.

### M5 — Decision engine L2 (Tier 2)
**Build:** constrained Monte Carlo sampler, Bayesian priors, Sobol sensitivity; `risk{}` in EngineResult.
**DoD:** deterministic under seed; samples respect L1 constraints; drivers computed.
**Acceptance T-M5:** fixed-seed run reproduces `p10/p50/p90`; win-prob monotone vs price; no sample violates a
hard L1 constraint.

### M6 — Email-broker + interactive kosztorys + auto-fill → **Tier 2 (Silnik) DONE**
**Build:** RFQ agent (gated send, IMAP parse), variable sidebar (`PATCH params`), chat-brain structured edits,
live rule-violation check, auto-fill draft (gated).
**DoD:** all external sends gated; chat edits applied by deterministic code; rules/check returns violations.
**Acceptance A2 (Tier 2 end-to-end):** A1 + engine verdict + risk distribution + an RFQ round-trip
(gated send → fixtured reply parsed) + an interactive param edit that reconciles. Auto-fill produces a draft,
never submits.

### M7 — Module 3 core (Tier 3)
**Build:** registries (equipment/employees/competency/availability/contracts), OR-Tools logistics optimizer,
plan assembly (`/plans`).
**DoD:** feasible assignment respects availability/competency; infeasible → explained.
**Acceptance T-M7:** fixture (2 contracts / 7 employees / limited excavators) → valid assignment;
over-constrained fixture → `engine_infeasible` with reason.

### M8 — Flutter mobile app (Tier 3)
**Build:** device registration, plan fetch/push, map pin/navigation, photos/drawings, offline cache (Drift),
field-status sync.
**DoD:** `flutter analyze` clean; offline plan available; queued status syncs on reconnect.
**Acceptance T-M8:** registered device fetches dispatched plan, opens pin, works offline, syncs a status.

### M9 — Orchestration, hardening, packaging → **Tier 3 (Mózg) DONE**
**Build:** LangGraph supervisor wiring M1→M2→M3 as one durable pipeline; dispatch (gated) to mobile+messenger;
learning loop on contract close; observability; backup/DR; Tauri installer + auto-update; first-run setup;
RODO employee notice; AI-literacy doc; Art.50 disclosure.
**DoD:** clean install boots green; full pipeline runs; all side-effects gated + audited; backups run.
**Acceptance A3 (Tier 3 full end-to-end):** fresh install → ingest → analyze → engine (L1+L2) → two-variant
estimate → go decision → contract → logistics optimize → daily plan → **gated dispatch** → mobile receives →
field status returns → on contract close, calibration updates. Every external action passed an approval gate
and wrote an audit row. Backup status green.

---

## Global "done" checklist (all tiers)
- [ ] Quality gates (spec/08) green; zero-network unit suite passes.
- [ ] Every external side-effect goes through the approval gate and writes audit (guard test proves it).
- [ ] No owner RMS/rate data in any cloud prompt (guard test proves it).
- [ ] Every engine flag and figure carries provenance; sums reconcile.
- [ ] `explanation_md` is the only LLM-authored field of `EngineResult`.
- [ ] OpenAPI covers all endpoints; contract tests pass.
- [ ] Tier feature-flags (`TIER=...`) correctly include/exclude modules and engine layers.
- [ ] `DECISIONS.md` records every assumption; `CHANGELOG.md` updated per milestone.

## If blocked
Prefer the simplest correct implementation, record the assumption, keep the gate's acceptance test as the
contract. Do not invent external facts (prices, regulatory dates, API schemas) — read from config and mark
`VERIFY`. When tender/document content conflicts with an assumption, the document wins (flag, don't fix).
