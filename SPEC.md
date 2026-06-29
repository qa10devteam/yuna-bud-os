# Terra.OS — Master Build Specification (SPEC.md)

**Audience:** an autonomous coding agent (Claude Code) building the platform end-to-end.
**Status:** implementation-ready · v1.0 · 2026-06-21 · QA10 Confidential
**Read order:** `CLAUDE.md` → this file → `spec/01..09` → build per `spec/09_milestones_acceptance.md`.

Product positioning and stylization: **Terra.OS** (exact). It is a *local, installed* system for earthworks
contractors: **Zwiad** (tender discovery), **Kosztorysant** (estimator), **Mózg** (management). The decision
core is an **axiomatic–stochastic engine**. Working UI mockup reference: `https://terra-os-opal.vercel.app/`.

---

## 1. Global locked decisions

| Area | Decision |
|---|---|
| Deployment | Installed desktop app — **Tauri 2** shell (Rust) packaging a **Next.js** static UI + Python sidecars |
| Backend | **Python 3.12 / FastAPI** local API; **LangGraph** durable agents; tools via MCP-style registry |
| Datastore | **PostgreSQL 16 + pgvector** (bundled, local); SQLAlchemy 2 + Alembic |
| Local AI | **Ollama** — Qwen3 (14–32B) for extraction/classification/routing; **Gemma 4 12B** (vision) for scanned-doc OCR |
| Cloud AI | **Claude on AWS Bedrock**, region `eu-central-1` (Frankfurt); prompt caching + Batch; tiered model selection |
| Decision engine | **L1** ASP (`clingo`) + SMT (`z3-solver`); **L2** constrained Monte Carlo + Sobol (NumPy/SciPy/SALib); **L3** neuro-symbolic orchestration. **MILP** via OR-Tools for Module 3 logistics |
| Mobile (Tier 3) | **Flutter 3.x** (iOS + Android) |
| Sources | BZP/e-Zamówienia read API, TED, Baza Konkurencyjności, municipal BIPs (4 voivodeships) |
| Tenancy | single-tenant; `tenant_id` on every operational table |
| Auth | none for desktop (single operator); per-device tokens for mobile sync |

All prices, regulatory dates, and external API schemas are **VERIFY** — read from config, never hardcoded as truth.

## 2. Tech stack & pinned tooling (record exact versions in lockfiles)

| Layer | Tool | Notes |
|---|---|---|
| Lang/runtime | Python 3.12, Node 20 LTS, Rust stable, Flutter stable | pin in `.tool-versions` |
| API | FastAPI, uvicorn, Pydantic v2 | |
| ORM/migrations | SQLAlchemy 2.0, Alembic | |
| Agents | LangGraph, langchain-core | durable checkpoints in Postgres |
| Engine | clingo (Python API), z3-solver, numpy, scipy, SALib, ortools | |
| AI clients | ollama (python), boto3 (Bedrock Runtime), anthropic (optional direct) | router abstracts both |
| Docs | pymupdf (text), a VLM-OCR path via Gemma (scanned), openpyxl (Excel), python-docx, lxml (.ath/XML) | |
| UI | Next.js 16 (output: export), React 19, TypeScript, Tailwind, CopilotKit/AG-UI | |
| Desktop | Tauri 2 (Rust) | sidecar supervision of Postgres/Ollama/API |
| Mobile | Flutter 3.x, Riverpod/Bloc, Drift (local cache) | Tier 3 |
| Quality | ruff, black, mypy, pytest, pytest-asyncio; eslint; flutter analyze | |
| CI | GitHub Actions; zero-network unit suite | |

## 3. Repository layout (monorepo)

```
terra-os/
├─ CLAUDE.md  SPEC.md  DECISIONS.md  CHANGELOG.md  .env.example  docker-compose.dev.yml  .tool-versions
├─ spec/                         # this specification (source of truth for behavior)
├─ apps/
│  ├─ desktop/                   # Tauri 2 shell (Rust) + installer + auto-update
│  ├─ ui/                        # Next.js static-export front-end (chat brain, lists, kosztorys editor)
│  └─ mobile/                    # Flutter app (Tier 3)
├─ services/
│  ├─ api/                       # FastAPI app: routers, dependency-injection, use-cases
│  ├─ agents/                    # LangGraph graphs: ingest, tracker, analysis, estimator, email_broker, dispatcher
│  ├─ engine/                    # decision engine: l1_symbolic/, l2_stochastic/, l3_orchestration/, axioms/
│  ├─ ingest/                    # connectors: bzp/, ted/, bk/, bip/ + normalize/
│  ├─ documents/                 # fetch/, ocr/, parse/ (przedmiar, STWiOR, .ath)
│  └─ ai/                        # router.py (Ollama|Bedrock), prompts/, cache.py, schemas.py
├─ packages/
│  ├─ db/                        # models.py (SQLAlchemy), migrations/ (alembic), ddl/ (canonical SQL)
│  └─ shared/                    # pydantic schemas, enums, provenance, errors, audit
└─ tests/                        # pytest + fixtures/ (recorded API responses, sample tenders/przedmiary)
```

## 4. Configuration (`.env`)

See `.env.example`. Key groups: `DB_*`, `OLLAMA_*`, `BEDROCK_*` (region `eu-central-1`), `BZP_API_BASE`,
`TED_*`, `BK_*`, `SMTP_*`/`IMAP_*`, `MESSENGER_*`, `MAPS_API_KEY`, `MOBILE_PUSH_*`, `FEATURE_FLAGS`,
`COST_CAPS` (per-day token budget), `APPROVAL_REQUIRED=true`. Never commit `.env`.

Tier gating is a feature-flag set: `TIER=fundament|silnik|mozg` toggles modules and engine layers so one
codebase ships all three tiers.

## 5. Cross-cutting patterns (implement once, reuse)

- **Provenance** (`packages/shared/provenance.py`): `Provenance{source, doc_id, page, line_or_pos, confidence}`.
  Every analytical output type embeds `provenance` and optional `flags: list[Flag]`.
- **Flag** (`Flag{code, severity: info|warn|block, message, provenance}`). "Don't guess → flag" returns a
  `Flag(severity=warn|block)` instead of a value.
- **Approval gate** (`services/api/approvals.py`): side-effectful actions create an `ApprovalRequest`,
  block until owner approves in UI, then execute and audit. No bypass path.
- **Audit** (`packages/shared/audit.py`): append-only writer; called by every agent step + every side-effect.
- **Cost guard** (`services/ai/cost.py`): per-call + per-day caps; Batch/cache preferred; refuse over cap.
- **LLM router** (`services/ai/router.py`): `route(task)` → local Ollama for high-volume/extraction,
  Bedrock-Claude for hard reasoning; redacts PII; never sends owner RMS data.

## 6. Spec index

| File | Contents |
|---|---|
| `spec/01_data_model.sql` | Canonical Postgres DDL (+ pgvector, RLS-ready, audit) |
| `spec/02_api_contracts.md` | Local REST endpoints, request/response shapes, error model |
| `spec/03_modules.md` | Module 1 (Zwiad), Module 2 (Kosztorysant), Module 3 (Mózg) — behavior + acceptance |
| `spec/04_decision_engine.md` | L1 (ASP/Z3) axioms + L2 (stochastic) + L3 orchestration; concrete examples |
| `spec/05_ai_and_ingestion.md` | LLM router/prompts/caching; connectors BZP/TED/BK/BIP; document pipeline |
| `spec/06_desktop_and_mobile.md` | Tauri packaging/sidecars/auto-update; Flutter mobile app |
| `spec/07_security_compliance.md` | RODO, EU AI Act Art.50/4, audit, backup/DR, approval gate |
| `spec/08_build_run_test.md` | Setup, commands, CI, test strategy, fixtures |
| `spec/09_milestones_acceptance.md` | Phase gates M0–M9 with Definition of Done + acceptance tests |

Begin at `spec/09` to see the gates, then implement M0 onward.
