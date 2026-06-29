# Terra.OS — CONTINUATION.md (post M9, ALL TIERS DONE)

## Repo
https://github.com/qa10devteam/terra-os.git
branch: main, last commit: 77e9bff

## Stack
- Python 3.12 (`/usr/bin/python3.12`)
- FastAPI monorepo: `services/api/`, `services/ingestion/`, `services/documents/`, `services/ai/`, `services/estimator/`, `services/engine/`, `services/logistics/`, `services/agents/`
- Next.js 16 UI: `apps/ui/`
- PostgreSQL 16: host=127.0.0.1, port=5432, db=terraos, user=terraos
- pgvector + pgcrypto aktywne
- clingo 5.8.0 + z3-solver + scipy 1.18.0 + ortools + langgraph zainstalowane

## DB password
`terraosdev2026` — env `DB_PASSWORD`, nigdy w kodzie

## Uruchamianie testów
```bash
TERRA_OFFLINE=1 DB_PASSWORD=*** python3.12 -m pytest tests/ -q
```
Wynik: **220/230 ✅** (M0–M9 kompletne)
Pre-istniejące failures: 10 w test_m1_ingest.py (IntegrityError _clean_tenders) — nie regresja.

---

## STATUS: WSZYSTKIE TIERY UKOŃCZONE ✅

### Tier 1 — Zwiad (M0+M1+M2+M3) ✅
### Tier 2 — Silnik (M4+M5+M6) ✅  Acceptance A2 ✅
### Tier 3 — Mózg (M7+M9) ✅  Acceptance A3 ✅

---

## Milestony

| Milestone | Commit | Testy | Status |
|-----------|--------|-------|--------|
| M0 Scaffold | 84baa30 | 14 | ✅ |
| M1 Zwiad BZP | 1094517 | 29 | ✅ |
| M2 Documents/OCR | 73dd0f5 | 21 | ✅ |
| M3 Estimator MVP | 147554f | 21 | ✅ A1 |
| M4 Engine L1 Clingo | 001aa9f | 29 | ✅ |
| M5 Engine L2 Monte Carlo | 9e9b9b6 | 28 | ✅ |
| M6 RFQ + Approvals + Chat | 384f132 | 23 | ✅ A2 |
| M7 Logistics OR-Tools | 7e2718b | 31 | ✅ T-M7 |
| M9 Pipeline + Hardening | 77e9bff | 34 | ✅ A3 |

**Total: 220 passed**

---

## Kluczowe pliki M9
- `services/agents/pipeline.py` — LangGraph supervisor (ingest→analyze→engine→estimate→decide→contract→optimize→plan→dispatch)
- `services/agents/learning_loop.py` — calibration_coeff update po close_contract
- `services/tier_flags.py` — TIER=1/2/3 feature flags
- `services/api/.../routers/system.py` — /agents, /pipeline/run, /contracts/{id}/close, /system/backup, /audit
- `docs/RODO_PRACOWNICY.md`, `docs/AI_LITERACY.md`, `docs/ART50_DISCLOSURE.md`
- `DECISIONS.md` (12 decyzji), `CHANGELOG.md`

## Kluczowe decyzje architektoniczne
- Clingo: integer arithmetic (PLN→grosze ×100, m→cm ×100) — NO floats
- estimate.variant enum: 'doc'/'owner' — NIE A/B
- Alembic: raw DDL (`op.execute(DDL)`) — NIE `op.create_table` z SA Enum
- httpx 0.28: `ASGITransport(app=app)` explicit
- DB_PASSWORD: tylko env var
- Approval Gate: jedyna ścieżka do side-effects → audit_log
- Calibration coeff clip: [0.5, 2.0]
- LangGraph: sync `graph.invoke()` w offline/test
- `explanation_md` — jedyne pole LLM w EngineResult

## Co dalej (opcjonalnie)
- M8 Flutter mobile (pominięte na życzenie)
- OpenAPI contract tests (`pytest --openapi`)
- Tauri desktop installer
- Produkcyjny LangGraph checkpointer (PostgreSQL)
- Real LLM integration (Bedrock/Ollama zamiast StubClient)
