# DISCOVERY.md — BudOS / YU-NA Architecture Audit
> Data audytu: 2026-07-21  
> Ścieżka repozytorium: `/home/ubuntu/terra-os`

---

## Struktura repo

```
terra-os/
├── apps/
│   └── ui/                         # Next.js frontend (App Router)
│       ├── src/
│       │   ├── app/                # Routing Next.js
│       │   │   ├── app/            # Główna sekcja aplikacji (po zalogowaniu)
│       │   │   │   ├── dashboard/
│       │   │   │   ├── zwiad/
│       │   │   │   ├── silnik/
│       │   │   │   ├── kosztorys/
│       │   │   │   ├── decyzja/
│       │   │   │   ├── rfq/
│       │   │   │   ├── documents/
│       │   │   │   ├── analytics/
│       │   │   │   ├── pipeline/
│       │   │   │   ├── notifications/
│       │   │   │   ├── settings/
│       │   │   │   ├── billing/
│       │   │   │   ├── icb/
│       │   │   │   ├── competitors/
│       │   │   │   ├── market-intel/
│       │   │   │   ├── automations/
│       │   │   │   ├── team/
│       │   │   │   ├── bookmarks/
│       │   │   │   ├── reports/
│       │   │   │   ├── proactive/
│       │   │   │   ├── oferta/
│       │   │   │   └── budos/      # Nowy moduł BudOS
│       │   ├── components/
│       │   │   ├── pages/          # Komponenty stron (~30 plików .tsx)
│       │   │   ├── widgets/        # KPIBar, MarketBar, CommandMenu, ChatWidget
│       │   │   └── layout/
│       │   ├── hooks/              # useRealtime.ts
│       │   ├── lib/                # api.ts, api-v2.ts, api-client.ts, tokens.ts
│       │   ├── store/              # useStore.ts (Zustand)
│       │   └── types/
├── services/
│   └── api/
│       └── services/api/
│           ├── main.py             # FastAPI app entry point (YU-NA API)
│           ├── auth/               # JWT auth (router.py, deps.py, utils.py, plan_gate.py)
│           ├── routers/            # ~70 routerów (lista poniżej)
│           ├── middleware/         # validation, rate_limit, tenant, csrf, ip_security, ids, audit_log
│           ├── analytics/          # cost_estimation, statystyki
│           ├── intelligence/       # buyer_score.py
│           └── agents/             # bzp_sync.py
├── packages/
│   ├── db/
│   │   ├── terra_db/
│   │   │   ├── models.py           # SQLAlchemy 2.0 modele
│   │   │   └── session.py          # DB engine/session
│   │   └── migrations/versions/    # Alembic (~27 migracji)
│   ├── shared/
│   │   └── terra_shared/           # provenance, flag, audit, errors
│   └── vendor/                     # vendored prompt_toolkit
├── infra/
│   ├── nginx/
│   ├── systemd/
│   └── terraform/modules/vllm/
├── data/
│   ├── qdrant_storage/             # Wektory (ddc_pl_warsaw, mercosur_eu_docs)
│   ├── bzp/
│   ├── gus/
│   ├── atlas/
│   └── sekocenbud/
├── docs/                           # bpmn, deploy, legal, security, research, performance
├── monitoring/
│   └── grafana/dashboards/
├── n8n-templates/
├── tests/                          # ~25 plików testów pytest
├── .env                            # VLLM_BASE_URL, VLLM_MODEL
├── .env.example                    # Pełny szablon konfiguracji
├── .env.local                      # N8N klucze
└── .env.prod                       # Produkcja (Postgres, Redis, Stripe)
```

---

## Backend endpoints

FastAPI app `YU-NA API v0.1.0` — serwer lokalny (127.0.0.1).  
Docs tylko w env `dev/test` (`/docs`, `/redoc`, `/openapi.json`).

### AUTH — `/api/v2/auth`

| METHOD | PATH | Opis | Params/Body |
|--------|------|------|-------------|
| POST | `/api/v2/auth/register` | Rejestracja | `{email, password, ...}` → `{access_token, refresh_token}` |
| POST | `/api/v2/auth/login` | Logowanie | `{email, password}` → `TokenResponse` |
| POST | `/api/v2/auth/refresh` | Odświeżenie tokenu | `{refresh_token}` → `TokenResponse` |
| POST | `/api/v2/auth/logout` | Wylogowanie (204) | `Authorization: Bearer` |
| POST | `/api/v2/auth/forgot-password` | Reset hasła — wysyłka maila | `{email}` |
| POST | `/api/v2/auth/reset-password` | Ustawienie nowego hasła | `{token, password}` |
| GET  | `/api/v2/auth/me` | Profil zalogowanego użytkownika | → `MeResponse` |
| GET  | `/api/v2/auth/me/full` | Pełny profil + org | `Authorization: Bearer` |
| POST | `/api/v2/auth/2fa/setup` | Konfiguracja TOTP 2FA | |
| POST | `/api/v2/auth/2fa/enable` | Włączenie 2FA | `{code}` |
| POST | `/api/v2/auth/2fa/disable` | Wyłączenie 2FA | `{code}` |

### TENDERS — `/api/v2/tenders`

| METHOD | PATH | Opis | Params |
|--------|------|------|--------|
| GET | `/api/v2/tenders` | Lista przetargów (paginacja) | `?sort=match_score&limit=N&status=...` |
| GET | `/api/v2/tenders/stats` | Agregaty/statystyki | |
| GET | `/api/v2/tenders/search` | Szybkie wyszukiwanie | `?q=...` |
| GET | `/api/v2/tenders/semantic-search` | FTS polish + ILIKE | `?q=...` |
| GET | `/api/v2/tenders/{tender_id}` | Szczegóły przetargu | path: `tender_id` |
| PATCH | `/api/v2/tenders/{tender_id}` | Zmień status | body: `{status}` |
| DELETE | `/api/v2/tenders/{tender_id}` | Archiwizuj | |
| POST | `/api/v2/tenders/{tender_id}/analyze` | Kolejkuj AI analysis | |
| GET | `/api/v2/tenders/{tender_id}/similar` | Podobne przetargi | |
| GET | `/api/v2/tenders/{tender_id}/score` | Match score (go/no-go %) | |
| POST | `/api/v2/tenders/ingest/run` | Uruchom ingest (async 202) | body: `IngestTaskRequest` |
| GET | `/api/v2/tenders/ingest/tasks/{task_id}` | Status ingestu | |
| GET | `/api/v2/tenders/ingest/tasks` | Lista zadań ingestu | |
| GET | `/api/v2/tenders/ingest/stream/{task_id}` | SSE stream ingestu | |
| POST | `/api/v2/tenders/ingest/cache/invalidate` | Invalidacja cache | |
| GET | `/api/v1/tenders` | Alias v1 → v2 (compat) | proxy do v2 |

### KOSZTORYS — `/api/v2/kosztorys`

| METHOD | PATH | Opis |
|--------|------|------|
| POST | `/api/v2/kosztorys/` | Nowy kosztorys |
| GET | `/api/v2/kosztorys/` | Lista kosztorysów |
| GET | `/api/v2/kosztorys/estimate` | Szacunek kosztów |
| GET | `/api/v2/kosztorys/material-alerts` | Alerty materiałowe |
| GET | `/api/v2/kosztorys/user-rates` | Stawki użytkownika |
| GET | `/api/v2/kosztorys/{kid}` | Szczegóły kosztorysu |
| PUT | `/api/v2/kosztorys/{kid}` | Aktualizacja |
| DELETE | `/api/v2/kosztorys/{kid}` | Usuń (204) |
| POST | `/api/v2/kosztorys/{kid}/recalc` | Przelicz |
| POST | `/api/v2/kosztorys/{kid}/intelligence` | AI Intelligence |
| GET | `/api/v2/kosztorys/{kid}/anomalies` | Wykrywanie anomalii |
| GET | `/api/v2/kosztorys/{kid}/win-probability` | Prawdopodobieństwo wygranej |
| POST | `/api/v2/kosztorys/{kid}/dzialy` | Dodaj dział |
| GET | `/api/v2/kosztorys/{kid}/dzialy` | Listy działów |
| DELETE | `/api/v2/kosztorys/{kid}/dzialy/{did}` | Usuń dział |
| POST | `/api/v2/kosztorys/{kid}/pozycje` | Dodaj pozycję |
| GET | `/api/v2/kosztorys/{kid}/pozycje` | Lista pozycji |
| PUT | `/api/v2/kosztorys/{kid}/pozycje/{pid}` | Aktualizuj pozycję |
| DELETE | `/api/v2/kosztorys/{kid}/pozycje/{pid}` | Usuń pozycję |
| POST | `/api/v2/kosztorys/{kid}/import-ath` | Import ATH |
| GET | `/api/v2/kosztorys/{kid}/export-pdf` | Eksport PDF |
| GET | `/api/v2/kosztorys/{kid}/export-ath` | Eksport ATH |
| GET | `/api/v2/kosztorys/{kid}/summary` | Podsumowanie |
| POST | `/api/v2/kosztorys/from-tender/{tender_id}` | Utwórz z przetargu |
| POST | `/api/v2/kosztorys/estimate` | Szybki szacunek |
| DELETE | `/api/v2/kosztorys/estimate/{estimate_id}` | Usuń szacunek |
| POST | `/api/v2/kosztorys/user-rates` | Dodaj stawkę |
| DELETE | `/api/v2/kosztorys/user-rates/{rate_id}` | Usuń stawkę |
| POST | `/api/v2/kosztorys/{kosztorys_id}/fork` | Fork kosztorysu |
| GET | `/api/v2/kosztorys/{kosztorys_id}/material-risk` | Ryzyko materiałowe |

### ANALYTICS — `/api/v2/analytics`

| METHOD | PATH | Opis |
|--------|------|------|
| POST | `/api/v2/analytics/cache/invalidate` | Invalidacja cache |
| GET | `/api/v2/analytics/dashboard` | Dane dashboard |
| GET | `/api/v2/analytics/pipeline-funnel` | Lejek pipeline |
| GET | `/api/v2/analytics/win-rate-trend` | Trend win rate |
| GET | `/api/v2/analytics/win-probability` | Pr. wygranej |
| POST | `/api/v2/analytics/ahp` | AHP multi-criteria |
| POST | `/api/v2/analytics/bidding` | Analiza przetargu |
| POST | `/api/v2/analytics/recommendation/{tender_id}` | Rekomendacja AI |
| POST | `/api/v2/analytics/risk-extract` | Ekstrakcja ryzyk |
| POST | `/api/v2/analytics/sensitivity` | Analiza wrażliwości |
| GET | `/api/v2/analytics/cost-trends` | Trendy kosztów |

### AI / AGENT PIPELINE — `/api/v2`

| METHOD | PATH | Opis |
|--------|------|------|
| POST | `/api/v2/ai/analyze-swz` | AI analiza SWZ |
| POST | `/api/v2/decisions/score` | Scoring decyzji |
| POST | `/api/v2/analytics/full-recommendation` | Pełna rekomendacja |
| POST | `/api/v2/analytics/feedback` | Feedback do modelu |
| GET | `/api/v2/reports/{tender_id}` | Raport przetargu |
| POST | `/api/v2/agent/analyze/{tender_id}` | Uruchom agenta AI |
| POST | `/api/v2/agent/decision/{tender_id}` | Decyzja przez agenta |
| GET | `/api/v2/agent/runs/{agent_run_id}` | Status przebiegu agenta |
| GET | `/api/v2/agent/brief/{tender_id}` | Krótkie streszczenie |
| GET | `/api/v2/agent/analyze/{tender_id}/stream` | SSE stream analizy |

### RFQ — `/api/v1` + `/api/v2/rfq`

| METHOD | PATH | Opis |
|--------|------|------|
| POST | `/api/v1/tenders/{tender_id}/rfq` | Utwórz RFQ (202) |
| GET | `/api/v1/rfq/{rfq_id}` | Szczegóły RFQ |
| POST | `/api/v1/rfq/{rfq_id}/inbound` | Odbierz ofertę |
| POST | `/api/v1/tenders/{tender_id}/autofill` | Autouzupełnienie |
| GET | `/api/v1/approvals` | Lista zatwierdzeń |
| POST | `/api/v1/approvals/{approval_id}/approve` | Zatwierdź |
| POST | `/api/v1/approvals/{approval_id}/reject` | Odrzuć |
| GET | `/api/v2/rfq` | Lista RFQ (v2) |

### DECISIONS — `/api/v2/decisions`

| METHOD | PATH | Opis |
|--------|------|------|
| GET | `/api/v2/decisions` | Lista decyzji |
| POST | `/api/v2/decisions` | Nowa decyzja |
| GET | `/api/v2/decisions/{decision_id}` | Szczegóły |
| POST | `/api/v2/decisions/bulk` | Masowe decyzje |

### ICB / CENY MATERIAŁÓW — `/api/v2/icb`

| METHOD | PATH | Opis |
|--------|------|------|
| POST | `/api/v2/icb/forecast/compute` | Prognoza cenowa |
| GET | `/api/v2/icb/forecast` | Wyniki prognozy |
| GET | `/api/v2/icb/search` | Wyszukiwanie materiałów |
| GET | `/api/v2/icb/suggest` | Podpowiedzi ICB |
| GET | `/api/v2/icb/categories` | Kategorie |
| GET | `/api/v2/icb/category/{category}/detail` | Szczegóły kategorii |
| GET | `/api/v2/icb/compare` | Porównanie cen |
| POST | `/api/v2/icb/basket` | Koszyk materiałowy |
| POST | `/api/v2/icb/kosztorys-autofill` | Autouzupełnienie kosztorysu |
| GET | `/api/v2/icb/dashboard` | Dashboard ICB |
| GET | `/api/v2/icb/robocizna/map` | Mapa stawek robocizny |
| GET | `/api/v2/icb/volatility-matrix` | Macierz zmienności cen |
| GET | `/api/v1/icb/suggest` | Alias v1 → v2 |
| GET | `/api/v1/icb/prices` | Alias v1 → v2 |

### BOOKMARKS / PIPELINE — `/api/v2/bookmarks`

| METHOD | PATH | Opis |
|--------|------|------|
| GET | `/api/v2/bookmarks/stats` | Statystyki Kanban |
| GET | `/api/v2/bookmarks` | Lista pipeline |
| GET | `/api/v2/bookmarks/export` | Eksport CSV |

### INTELLIGENCE — `/api/v2/intelligence`

| METHOD | PATH | Opis |
|--------|------|------|
| GET | `/api/v2/intelligence/summary` | Podsumowanie rynkowe |
| GET | `/api/v2/intelligence/trends` | Trendy CPV |
| GET | `/api/v2/intelligence/competitors/top` | Top konkurenci |
| GET | `/api/v2/intelligence/buyers/top` | Top zamawiający |
| GET | `/api/v2/intelligence/prices/inflation` | Inflacja cenowa |
| GET | `/api/v2/intelligence/fts` | Pełnotekstowe szukanie |
| GET | `/api/v2/intelligence/win-rates` | Win rates |
| GET | `/api/v2/intelligence/top-buyers-cpv` | Top kupujący wg CPV |
| GET | `/api/v2/intelligence/seasonality` | Sezonowość |
| GET | `/api/v2/intelligence/benchmark` | Benchmark |
| GET | `/api/v2/intelligence/win-probability` | Pr. wygranej |
| GET | `/api/v2/intelligence/prices/index` | Indeks cenowy |

### POZOSTAŁE WAŻNE ROUTERY

| Prefix | Opis |
|--------|------|
| `/api/v2/bzp` | BZP v2 — sync, status, tenders |
| `/api/v2/buyer-crm` | CRM zamawiających |
| `/api/v2/competitors` | Obserwacja konkurencji |
| `/api/v2/scoring` | Konfiguracja scoringu, breakdowns |
| `/api/v2/notifications` | Powiadomienia |
| `/api/v2/documents` | Upload dokumentów v2 |
| `/api/v2/estimates` | Kosztorysy v2 |
| `/api/v2/search` | Globalne wyszukiwanie |
| `/api/v2/audit` | Logi audytowe |
| `/api/v2/billing` | Stripe billing |
| `/api/v2/gdpr` | Zgody RODO |
| `/api/v2/api-keys` | Zarządzanie kluczami API |
| `/api/v2/organizations` | Organizacje / multi-tenant |
| `/api/v2/automations` | Automatyzacje (n8n) |
| `/api/v2/gantt` | Wykres Gantta |
| `/api/v2/workflows` | Przepływy pracy |
| `/api/v2/forecast` | Prognozowanie |
| `/api/v2/proactive` | Proaktywne alerty |
| `/api/v2/bid-writing` | AI szkielet oferty |
| `/api/v2/swz` | Asystent SWZ |
| `/api/v2/validation` | Walidacja 47-punktowa PZP |
| `/api/v2/reports` | Raporty |
| `/api/v2/chat` | Chat AI |
| `/api/v2/ai-chat` | AI Chat (nowy) |
| `/api/v2/market-intelligence` | Wywiady rynkowe |
| `/api/v2/external` | Dane zewnętrzne (TED, GUS, pre-tender) |
| `/api/v2/uzp` | UZP Change Tracker |
| `/api/v2/data-quality` | Jakość danych |
| `/api/v2/feature-flags` | Feature flags |
| `/api/v2/ab` | A/B testing |
| `/api/v2/integrations` | Integracje zewnętrzne |
| `/api/v2/submit` | Submit Wizard |
| `/api/v1/comments` | Komentarze do przetargów |
| `/api/v1/market` | Dane rynkowe (kursy, pogoda) |
| `/api/v1/email` | Konfiguracja email |
| `/api/v1/webhooks` | Webhooks przychodzące |
| `/api/v1/bzp/documents` | Dokumenty BZP |
| `/api/v1/subcontractors` | Podwykonawcy |
| `/api/v1/equipment` | Sprzęt |
| `/api/v1/resources/employees` | Pracownicy |
| `/api/v1/contracts` | Kontrakty |
| `/api/v1/verify` | Weryfikacja KRS |
| `/api/v1/gus` | Dane GUS BDL |
| `/api/v1/sse` | SSE stream |
| `/api/v1/mcp` | MCP chat |
| `/api/v1/playground` | Playground AI |
| `/metrics` | Prometheus metrics (secured) |
| `/health` | Health check |
| `/api/v2/demo` | Demo dane (dev) |

---

## DB Schema

Baza danych: **PostgreSQL** z **Row-Level Security (RLS)** per-tenant.  
ORM: **SQLAlchemy 2.0**, migracje **Alembic** (~27 wersji).  
Rozszerzenia: `pgvector` (embeddingi), `pg_trgm` (FTS), `btree_gist`.

### Tabele kluczowe

| Tabela | Kluczowe kolumny | Relacje |
|--------|-----------------|---------|
| `tenant` | `id (PK, UUID)`, `name`, `created_at` | Root — wszystkie tabele FK do tenant |
| `owner_profile` | `id`, `tenant_id`, `company_name`, `cpv_preferred[]`, `voivodeships[]`, `equipment (JSONB)`, `references_md` | FK → tenant |
| `tender` | `id`, `tenant_id`, `source (bzp/ted/bk/bip)`, `external_id`, `title`, `buyer`, `cpv[]`, `voivodeship`, `value_pln`, `deadline_at`, `published_at`, `url`, `status (enum)`, `match_score`, `match_reason`, `raw (JSONB)` | FK → tenant; UNIQUE(tenant_id, source, external_id) |
| `tender_document` | `id`, `tenant_id`, `tender_id`, `kind`, `filename`, `local_path`, `mime`, `pages`, `parsed_ok` | FK → tender |
| `document_chunk` | `id`, `tenant_id`, `document_id`, `page`, `ordinal`, `content`, `embedding (vector 1024)` | FK → tender_document |
| `przedmiar_item` | `id`, `tenant_id`, `tender_id`, `document_id`, `position_no`, `knr_code`, `description`, `unit`, `quantity` | FK → tender, tender_document |
| `analysis` | `id`, `tenant_id`, `tender_id`, `summary_md` | FK → tender |
| `discrepancy` | `id`, `tenant_id`, `tender_id`, `kind`, `severity (info/warn/block)`, `message`, `provenance (JSONB)`, `axiom_id` | FK → tender, axiom |
| `estimate` | `id`, `tenant_id`, `tender_id`, `variant (doc/owner)`, `total_net_pln`, `overhead_pct`, `profit_pct`, `params (JSONB)` | FK → tender |
| `estimate_line` | `id`, `tenant_id`, `estimate_id`, `description`, `unit`, `quantity`, `unit_price`, `labor_pln`, `material_pln`, `equipment_pln`, `line_total_pln` | FK → estimate |
| `rate_card` | `id`, `tenant_id`, `key`, `unit`, `rate_pln`, `efficiency`, `source`, `valid_from` | FK → tenant; UNIQUE(tenant_id, key, valid_from) |
| `calibration_coeff` | `id`, `tenant_id`, `key`, `coeff`, `variance`, `version` | FK → tenant |
| `rfq` | `id`, `tenant_id`, `tender_id`, `scope_desc`, `status (draft/sent/awaiting/received/parsed/closed)` | FK → tender |
| `rfq_message` | `id`, `tenant_id`, `rfq_id`, `direction`, `counterparty`, `subject`, `body`, `parsed_offer (JSONB)` | FK → rfq |
| `axiom` | `id`, `tenant_id`, `class (regulatory/documentary/engineering/economic)`, `code`, `body`, `version`, `active` | FK → tenant; UNIQUE(tenant_id, code, version) |
| `risk_run` | `id`, `tenant_id`, `tender_id`, `estimate_id`, `samples`, `margin_p10/p50/p90`, `win_prob_at_price (JSONB)`, `drivers (JSONB)` | FK → tender, estimate |
| `resource_equipment` | `id`, `tenant_id`, `type`, `model`, `reg_no`, `capacity (JSONB)`, `active` | FK → tenant |
| `employee` | `id`, `tenant_id`, `name`, `phone`, `role`, `active` | FK → tenant |
| `competency` | `id`, `tenant_id`, `employee_id`, `skill`, `level` | FK → employee |
| `availability` | `id`, `tenant_id`, `employee_id?`, `equipment_id?`, `day`, `available`, `note` | FK → employee lub equipment |
| `contract` | `id`, `tenant_id`, `tender_id?`, `title`, `state`, `start_date`, `end_date`, `lat`, `lng` | FK → tender |
| `calendar_event` | `id`, `tenant_id`, `contract_id?`, `day`, `title`, `equipment_ids[]`, `employee_ids[]` | FK → contract |
| `daily_plan` | `id`, `tenant_id`, `contract_id?`, `day`, `location_address`, `lat/lng`, `photos (JSONB)`, `drawings (JSONB)`, `status (draft/dispatched/acknowledged/in_progress/done)` | FK → contract |
| `dispatch` | `id`, `tenant_id`, `daily_plan_id`, `employee_id?`, `channel`, `sent_at`, `acknowledged_at` | FK → daily_plan, employee |
| `field_status` | `id`, `tenant_id`, `daily_plan_id?`, `employee_id?`, `note`, `photos (JSONB)` | FK → daily_plan |
| `mobile_device` | `id`, `tenant_id`, `employee_id?`, `device_token (unique)`, `platform`, `push_token` | FK → employee |
| `approval_request` | `id`, `tenant_id`, `action`, `payload (JSONB)`, `status (pending/approved/rejected/expired)`, `requested_at`, `decided_at`, `decided_by` | FK → tenant |
| `agent_run` | `id`, `tenant_id`, `agent`, `status (queued/running/paused/succeeded/failed/cancelled)`, `input/output/state (JSONB)`, `tokens_in/out`, `cost_pln`, `error` | FK → tenant |
| `audit_log` | `id (BigInt autoincrement)`, `tenant_id`, `at`, `actor`, `action`, `entity`, `entity_id`, `detail (JSONB)` | Append-only; FK → tenant |

### Statusy enum

```
tender_status:    new | matched | watching | analyzing | estimated | decided_go | decided_nogo | archived
source_kind:      bzp | ted | bk | bip
flag_severity:    info | warn | block
estimate_variant: doc | owner
approval_status:  pending | approved | rejected | expired
agent_status:     queued | running | paused | succeeded | failed | cancelled
rfq_status:       draft | sent | awaiting | received | parsed | closed
axiom_class:      regulatory | documentary | engineering | economic
plan_status:      draft | dispatched | acknowledged | in_progress | done
```

### Stan bazy

> **UWAGA:** Baza PostgreSQL lokalnie **niedostępna** podczas audytu (brak działającego serwisu). Schema pochodzi z analizy kodu SQLAlchemy + migracji Alembic.

---

## Auth flow

### Mechanizm: JWT (HS256) + Refresh Token

```
1. POST /api/v2/auth/register lub /login
   → zwraca: { access_token: string, refresh_token: string, token_type: "bearer" }

2. Każde żądanie API:
   Header: Authorization: Bearer <access_token>
   Backend: HTTPBearer scheme → decode_access_token() → PyJWT.decode(token, SECRET_KEY, HS256)
   Payload JWT: { user_id, email, org_id, role, type: "access" }

3. Wygaśnięcie access_token (401):
   Frontend (api.ts): automatycznie POST /api/v2/auth/refresh z { refresh_token }
   → nowy access_token + zapis do Zustand store
   → przy niepowodzeniu: clearAuth() + redirect /auth/login

4. Refresh token:
   - Przechowywany jako SHA256 hash w tabeli (nie jako JWT)
   - Generowany jako `secrets.token_urlsafe()`
   - raw_token → hash_sha256 → zapisany w DB

5. 2FA (TOTP):
   POST /api/v2/auth/2fa/setup → generuje TOTP secret (QR)
   POST /api/v2/auth/2fa/enable (code) → weryfikacja TOTP
   POST /api/v2/auth/2fa/disable (code)
   Kolumny DB (migracja 0026): totp_secret, totp_enabled

6. Bezpieczeństwo dodatkowe:
   - CSRF middleware (X-CSRF-Token header)
   - IP Security middleware (blocklist)
   - IDS middleware — anomaly detection (threshold=20 req/5min, block TTL=1h)
   - Rate limiter — sliding window 100 req/min per user/IP
   - Tenant middleware + RLS — każde zapytanie filtrowane po tenant_id
   - Security headers: HSTS, X-Frame-Options DENY, Referrer-Policy
   - CORS: origins z env ALLOWED_ORIGINS (default: localhost:3000)
```

### Plan gating
```
auth/plan_gate.py → require_plan(PlanLevel)
Tiery: fundament | silnik | mozg (z .env.example: TIER=silnik)
APPROVAL_REQUIRED=true — każda akcja AI wymaga zatwierdzenia przez człowieka
```

---

## Frontend modules

### App Router — `/app/app/` + komponenty pages

| Moduł (route) | Komponent strony | Status | Typ API calls |
|---------------|-----------------|--------|---------------|
| `zwiad` | `ZwiadPage.tsx` | **MOCK** | Tylko dane lokalne — brak wywołań fetch do backendu |
| `silnik` | `SilnikPage.tsx` | **REAL** | `/api/v2/tenders`, `/api/v2/scoring/config`, `/api/v2/estimates`, `/api/v2/icb/suggest`, `/api/v2/intelligence/*` |
| `kosztorys` | `KosztorysPage.tsx` | **REAL** | `/api/v2/kosztorys`, `/api/v2/estimates`, `/api/v1/bzp/documents/{id}/fetch` |
| `dashboard` | `DashboardPage.tsx` | **REAL** | `/api/v2/analytics/dashboard`, `/api/v2/tenders` |
| `analytics` | `AnalyticsPage.tsx` | **REAL** | `/api/v2/analytics/*` |
| `decyzja` | `DecyzjaPage.tsx` | **REAL** | `/api/v2/decisions`, AI endpoints |
| `rfq` | `RfqPage.tsx` | **REAL** | `/api/v1/rfq/*`, `/api/v1/approvals` |
| `pipeline` | `PipelinePage.tsx` | **REAL** | `/api/v2/bookmarks`, `/api/v2/bookmarks/stats` |
| `icb` | `ICBPage.tsx` | **REAL** | `/api/v2/icb/*` |
| `competitors` | `CompetitorPage.tsx` | **REAL** | `/api/v2/competitors`, `/api/v2/intelligence/*` |
| `market-intel` | `MarketIntelPage.tsx` | **REAL** | `/api/v2/intelligence/*` |
| `notifications` | `NotificationsPage.tsx` | **REAL** | `/api/v2/notifications`, `/api/v2/alerts` |
| `documents` | `DocumentsPage.tsx` | **REAL** | `/api/v2/documents`, `/api/v1/bzp/documents` |
| `automations` | `AutomationPage.tsx` | **REAL** | `/api/v2/automations`, n8n |
| `reports` | `ReportsPage.tsx` | **REAL** | `/api/v2/reports` |
| `settings` | `SettingsPage.tsx` | **REAL** | `/api/v2/scoring/config`, `/api/v2/api-keys`, `/api/v2/gdpr` |
| `oferta` | `OfertaPage.tsx` | **REAL** | `/api/v2/offers`, `/api/v2/bid-writing` |
| `proactive` | `ProactivePage.tsx` | **REAL** | `/api/v2/proactive/*` |
| `bid-intelligence` | `BidIntelligencePage.tsx` | **REAL** | `/api/v2/intelligence/*` |
| `team` | `TeamPage.tsx` | **REAL** | `/api/v2/organizations/me/members` |
| `logistyka` | `LogistykaPage.tsx` | **REAL** | `/api/v1/logistics`, `/api/v1/contracts` |
| `pogoda` | `PogodaPage.tsx` | **REAL** | `/api/v1/market/weather/*` |
| `axiom` | `AxiomEnginePage.tsx` | **REAL** | `/api/v2/swz`, axiom endpoints |
| `bookmarks` | `BookmarksBoardPage.tsx` | **REAL** | `/api/v2/bookmarks` |
| `export` | `ExportPage.tsx` | **REAL** | `/api/v1/export/*` |
| `webhooks` | `WebhooksPage.tsx` | **REAL** | `/api/v2/integrations`, `/api/v1/webhooks` |
| `system` | `SystemPage.tsx` | **REAL** | `/api/v1/system/*`, health |
| `budos` | (nowy, minimal) | **SKELETON** | Brak implementacji |

### Kluczowe biblioteki frontend

- **State**: Zustand (`useStore.ts`) — accessToken, refreshToken, setAuth, clearAuth
- **API Client**: 
  - `api-client.ts` — deduplikacja requestów, interceptory 401/429/500
  - `api.ts` — hooks z retry + auto-refresh
  - `api-v2.ts` — hooks dla intelligence/alerts/bookmarks/competitors
- **Realtime**: `useRealtime.ts` — WebSocket / SSE hook
- **UI**: Tailwind CSS, motion/react (Framer Motion), lucide-react, Radix UI

---

## Zewnętrzne zależności

| Zależność | Typ | Użycie | Konfiguracja |
|-----------|-----|--------|--------------|
| **PostgreSQL** | DB | Główna baza danych + pgvector + pg_trgm | `DB_HOST/PORT/NAME/USER/PASSWORD` |
| **Redis** | Cache/Queue | Cache, rate-limiting, session | `REDIS_HOST/PORT/PASSWORD` |
| **BZP API** (ezamowienia.gov.pl) | Zewnętrzne API | Ingest przetargów publicznych PL | `BZP_API_BASE` |
| **TED API** (ted.europa.eu) | Zewnętrzne API | Przetargi europejskie (opcjonalnie) | `TED_API_BASE` |
| **NBP / kursy walut** | Zewnętrzne API | `GET /api/v1/market/currencies` | wbudowane |
| **Pogoda** | Zewnętrzne API | `GET /api/v1/market/weather/*` | wbudowane |
| **Ollama** (lokalny LLM) | AI | qwen3:14b/32b (ekstrakcja), gemma3:12b (OCR), nomic-embed-text | `OLLAMA_HOST/MODEL_*` |
| **AWS Bedrock** (cloud AI) | AI | claude-sonnet-4-6 (domyślny), claude-haiku (lekki) | `BEDROCK_REGION/MODEL`, `AWS_ACCESS_KEY_ID/SECRET` |
| **vLLM** | AI | Lokalny LLM server (axon model) | `VLLM_BASE_URL=http://localhost:8001/v1` |
| **Qdrant** | Wektorowa DB | Embeddingi dokumentów — kolekcje: `ddc_pl_warsaw`, `mercosur_eu_docs` | lokalne `data/qdrant_storage/` |
| **n8n** | Automatyzacje | Webhooks, przepływy automatyzacji | `N8N_BASE_URL=http://localhost:5678`, `N8N_API_KEY` |
| **Stripe** | Billing | Płatności SaaS (Pro, Business) | `STRIPE_SECRET_KEY`, `STRIPE_PRICE_PRO/BUSINESS`, `STRIPE_WEBHOOK_SECRET` |
| **SMTP/IMAP** | Email | Broker email RFQ, powiadomienia | `SMTP_HOST/PORT/USER/PASSWORD`, `IMAP_*` |
| **APScheduler** | Cron | BZP auto-sync co 15 minut | wbudowane |
| **Prometheus** | Monitoring | `/metrics` endpoint | `METRICS_TOKEN` (opcjonalnie) |
| **Grafana** | Monitoring | Dashboardy, `monitoring/grafana/` | lokalne |
| **GUS BDL** | Zewnętrzne API | Dane statystyczne GUS | `/api/v1/gus/*` |
| **KRS** | Zewnętrzne API | Weryfikacja podmiotów | `/api/v1/verify` |
| **FCM** (Firebase) | Mobile push | Powiadomienia mobilne (Tier 3) | `MOBILE_PUSH_PROVIDER=fcm` |
| **WhatsApp/Telegram** | Messenger | Dyspozytornia mobilna (Tier 3) | `MESSENGER_PROVIDER/TOKEN` |
| **Sekocenbud** | Dane cenowe | Katalog ICB — `data/sekocenbud/` | lokalne pliki |

---

## Kluczowe luki i ryzyka

### 🔴 Krytyczne

| # | Luka | Opis | Ryzyko |
|---|------|------|--------|
| R1 | **JWT_SECRET niezabezpieczony** | `.env.example` zawiera `terra-dev-secret-change-in-production-xyz` — kod sprawdza czy jest ustawiony, ale nie waliduje złożoności | Wyciek tokenów, pełna kompromitacja sesji |
| R2 | **PostgreSQL niedostępny lokalnie** | Baza nie działa podczas audytu — nie można zweryfikować stanu danych, migracji, RLS | Niemożność testowania live |
| R3 | **Dokumentacja API tylko w dev/test** | `/docs` i `/redoc` wyłączone w produkcji — brak zewnętrznego OpenAPI | Utrudniona integracja, trudność debugowania |
| R4 | **Moduł Zwiad — MOCK data** | `ZwiadPage.tsx` operuje wyłącznie na danych lokalnych bez wywołań API | Frontend pokazuje fikcyjne dane; moduł de facto niedziałający |

### 🟡 Wysokie

| # | Luka | Opis | Ryzyko |
|---|------|------|--------|
| R5 | **Brak separacji v1/v2 endpointów** | Wiele routerów nadal na `/api/v1` (chat, engine, estimator, export, comments, resources) — kod v1 niegdyż deprecated | Utrudnione wersjonowanie, tech debt |
| R6 | **FIELD_ENCRYPTION_KEY opcjonalny** | `.env.example` ma `FIELD_ENCRYPTION_KEY=` (puste) — szyfrowanie pól wrażliwych nie jest wymuszane | Dane PII/wrażliwe mogą nie być szyfrowane |
| R7 | **Graceful import optional routers** | ~30 routerów ładowanych przez `try/except ImportError` — błąd importu jest cicho ignorowany | Feature może być nieaktywny bez alertu |
| R8 | **BudOS module — Skeleton** | Folder `/app/app/budos/` istnieje ale jest minimalny — brak pełnej implementacji | Niezgodność między roadmapą a stanem kodu |
| R9 | **Duplikaty routerów** | `audit.py` i `audit_v2.py` obie na `/api/v2/audit`; `kosztorys.py` (v1 deprecated) + `kosztorys_v2.py` + `kosztorys_v3.py` — ryzyko kolizji ścieżek | Nieprzewidywalne zachowanie, trudność maintenance |
| R10 | **APPROVAL_REQUIRED hard dependency** | Ustawione w .env jako `APPROVAL_REQUIRED=true` — każda akcja AI wymaga ludzkiej decyzji; brak automatyzacji | Bottleneck operacyjny |

### 🟠 Średnie

| # | Luka | Opis |
|---|------|------|
| R11 | **Wiele modeli LLM bez fallback logiki** | 3 różne LLM backends (Ollama, Bedrock, vLLM) — brak widocznej logiki failover |
| R12 | **COST_CAP_DAILY_PLN=50** | Dzienny limit AI costs 50 PLN — może blokować intensywne użycie |
| R13 | **Brak rate limiting na poziomie nginx** | Rate limiting tylko w FastAPI middleware — brak obrony przed DDoS na poziomie proxy |
| R14 | **n8n bez auth w dev** | `N8N_BASE_URL=http://localhost:5678` — lokalne n8n może być dostępne bez uwierzytelnienia |
| R15 | **api-client.ts 500/503 → null** | Globalny interceptor zwraca `null` przy błędach serwera — błędy mogą być maskowane UI |
| R16 | **Qdrant bez autentykacji** | Dane wektorowe w `data/qdrant_storage/` lokalnie — brak widocznej konfiguracji auth |
| R17 | **Tenant isolation via app-layer RLS** | RLS jest instalowane przez middleware Pythona — nie jest natywnym PostgreSQL RLS; błąd w middleware = wyciek między tenantami |

### 🔵 Do rozwiązania (tech debt)

| # | Dług |
|---|------|
| D1 | Stary moduł `kosztorys.py` (v1 deprecated) powinien być usunięty |
| D2 | `v1_tenders_list` proxy używa `httpx` do siebie samego (localhost:8000) — anti-pattern, może powodować deadlocki |
| D3 | `packages/vendor/prompt_toolkit` — vendored dependency zamiast pip — problem z aktualizacjami |
| D4 | `ChatWidget.tsx` istnieje w dwóch miejscach (`components/` i `components/widgets/`) |
| D5 | Frontend `api.ts` i `api-v2.ts` i `api-client.ts` — 3 różne warstwy fetch, brak unifikacji |
| D6 | Brak `.env.prod` w `.gitignore` (zawiera kredencjale Stripe, DB passwords) — **KRYTYCZNE dla security** |

---

## Podsumowanie techniczne

```
Platforma:  YU-NA / BudOS / Terra.OS
Typ:        SaaS B2B — platforma decyzyjna dla wykonawców przetargów publicznych (PL)
Backend:    FastAPI (Python 3.12) — ~70 routerów, ~350+ endpointów
Frontend:   Next.js (App Router) — ~25 modułów stron, Zustand state, 3 warstwy API client
Baza:       PostgreSQL + pgvector + pg_trgm — ~25 tabel, RLS per-tenant, Alembic migrations
Cache:      Redis
AI Stack:   Ollama (lokalny) + AWS Bedrock (cloud) + vLLM (fine-tuned axon)
Wektoryzacja: Qdrant + nomic-embed-text (1024 dim)
Automatyzacje: n8n (templates)
Billing:    Stripe (Pro/Business tiers)
Monitoring: Prometheus + Grafana
Auth:       JWT (HS256) + Refresh token + TOTP 2FA + CSRF + IDS + IP blocklist
Tier system: fundament | silnik | mozg
```
