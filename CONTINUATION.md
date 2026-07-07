# TERRA.OS — KONTYNUACJA PRAC
## Ostatnia aktualizacja: 07.07.2026 | Senior Developer — Agency Agents NEXUS

---

## STATUS PROJEKTU

| Faza | Opis | Stan | Data |
|------|------|------|------|
| ☑ Faza 1 | Bootstrap: FastAPI + Next.js + PostgreSQL, multi-tenant core | ✅ ZAMKNIĘTA | 07.07.2026 |
| ☑ Faza 2 | DB Schema v2: 76 tabel, 10 MV, pgvector, RLS, indeksy, dane rynkowe | ✅ ZAMKNIĘTA | 07.07.2026 |
| ☑ Faza 3 | Backend API v2: 5 routerów, audit SWISS WATCH (92+65 testów) | ✅ ZAMKNIĘTA | 07.07.2026 |
| ☑ Faza 4 | UI Analityczny: MarketIntelPage, CompetitorPage, BookmarksBoardPage | ✅ ZAMKNIĘTA | 07.07.2026 |
| ☑ Faza 5 | UI CRM+Settings: BuyerCRMPage, SettingsPage, NotificationsPage, ExportPage | ✅ ZAMKNIĘTA | 07.07.2026 |
| ☑ **Faza 6** | **Zwiad + Kosztorys + Logistyka (3 filary, 67/67 testów)** | **✅ ZAMKNIĘTA** | **07.07.2026** |
| 🔄 **Faza 7** | **Oferta: moduł offers, PDF export, integracja z przetargami** | **🔄 W TOKU** | **07.07.2026** |

---

## AKTYWNY STAN (07.07.2026)

### Serwisy
- **API:** `http://localhost:8000` — FastAPI, db ✅, redis ✅
- **UI:** `http://localhost:3000` — Next.js 15
- **DB:** PostgreSQL 16, user `terraos` / `terra_dev_2026`, baza `terraos`
- Demo user: `demo@terra-os.pl` / `demo2026!`
- Demo tenant: `ec3d1e16-2139-48c2-93b5-ffe0defd606d`

### Repo
- `/home/ubuntu/terra-os/` — branch `main`
- `.venv` aktywny w `/home/ubuntu/terra-os/.venv`
- `pytest.ini` — `pythonpath = . services/api`

### Build i testy
- **TypeScript build:** 0 błędów ✅ (Next.js 15)
- **Test suite Faza 5:** 42/42 ALL PASS ✅
- **Test suite Faza 6:** 67/67 ALL PASS ✅ (Zwiad + Kosztorys + Logistyka)
- **API audit:** 92/92 ✅ + 65/65 deep audit ✅ (Faza 3)
- **Średni response time API:** 71ms

---

## FAZA 6 — ZWIAD + KOSZTORYS + LOGISTYKA ✅ ZAMKNIĘTA (07.07.2026)

### Trzy filary — dostarczone

| Filar | Opis | Stan |
|-------|------|------|
| **Zwiad** (Tender Intelligence) | Śledzenie, analiza i scoring przetargów | ✅ DONE |
| **Kosztorys** (Smart Estimator) | AI-powered kosztorysowanie z bazą Sekocenbud/ICB | ✅ DONE |
| **Logistyka** | Planowanie zasobów: pracownicy, sprzęt, optymalizacja | ✅ DONE |

### Nowe pliki UI

```
apps/ui/src/components/pages/ZwiadPage.tsx      -- Agent 1
apps/ui/src/components/pages/KosztorysPage.tsx  -- Agent 2
apps/ui/src/components/pages/LogistykaPage.tsx  -- Agent 3
```

### Wynik
- Build: **0 błędów TypeScript** ✅
- Testy: **67/67 ALL PASS** ✅ (`/tmp/test_faza6.py`)
- UI renderuje wszystkie 3 moduły (Zwiad, Kosztorys, Logistyka)

### Backend Fazy 6 — endpointy

#### ZWIAD (Tender Intelligence)
```
GET  /api/v1/tenders              -- lista aktywnych przetargów (feed BZP)
POST /api/v1/ingest/run           -- uruchom ingest (pobierz nowe przetargi)
GET  /api/v2/intelligence/fts     -- FTS search na historical_tenders
GET  /api/v2/intelligence/benchmark -- benchmark CPV/region/kwartał
GET  /api/v2/intelligence/trends  -- trendy rynkowe
GET  /api/v2/intelligence/seasonality -- sezonowość
```

#### KOSZTORYS (Smart Estimator)
```
POST /api/v2/estimates/predict    -- AI predykcja kosztu (CPV, region, wartość)
GET  /api/v1/kosztorys/           -- lista kosztorysów
POST /api/v1/kosztorys/           -- utwórz kosztorys
GET  /api/v1/kosztorys/{id}       -- szczegóły kosztorysu
PUT  /api/v1/kosztorys/{id}       -- aktualizuj kosztorys
GET  /api/v1/kosztorys/{id}/items -- pozycje kosztorysu
```

#### LOGISTYKA
```
GET  /api/v1/resources/employees    -- lista pracowników (85 rekordów)
GET  /api/v1/resources/equipment    -- lista sprzętu
POST /api/v1/logistics/optimize     -- optymalizacja przydziału zasobów
GET  /api/v1/resources/availability -- dostępność (119 rekordów)
```

---

## FAZA 7 — OFERTA 🔄 W TOKU

### Cel Fazy 7

Moduł **Oferta** pozwala tworzyć, zarządzać i eksportować (PDF) oferty składane na przetargi.
Jest mostem między przetargiem (Faza 6 Zwiad) a formalnym dokumentem ofertowym.

### Backend — endpointy do implementacji

```
GET    /api/v1/offers              -- lista ofert {total, items}, filtr ?status=
POST   /api/v1/offers              -- utwórz ofertę {title, status, tender_id?, ...}
GET    /api/v1/offers/{id}         -- pojedyncza oferta
PATCH  /api/v1/offers/{id}         -- aktualizacja pól (status, title, ...)
DELETE /api/v1/offers/{id}         -- usuń ofertę
GET    /api/v1/offers/{id}/pdf     -- eksport PDF (Content-Type: application/pdf)
```

### DB — tabela `offers`

Minimalne wymagane kolumny:
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
tenant_id   UUID NOT NULL REFERENCES tenant(id)
tender_id   UUID REFERENCES tender(id)   -- opcjonalne powiązanie
title       TEXT NOT NULL
status      TEXT NOT NULL DEFAULT 'draft'  -- draft | ready | submitted | won | lost
created_at  TIMESTAMPTZ DEFAULT now()
updated_at  TIMESTAMPTZ DEFAULT now()
```

### Agenci w locie

| Agent | Zadanie | Deliverable |
|-------|---------|-------------|
| Agent 1 (Backend Developer NEXUS) | Implementacja `offers.py` + migracja DB | Router FastAPI + tabela offers |
| Agent 2 (Frontend Developer NEXUS) | Implementacja `OfertaPage.tsx` | Strona Oferta z listą, statusem, linkiem do PDF |
| Agent 3 (API Tester NEXUS) | Test suite `/tmp/test_faza7.py` | 30+ testów CRUD + PDF + integration ✅ GOTOWE |

### Test Suite Fazy 7

Plik: `/tmp/test_faza7.py` — **GOTOWY** ✅

Sekcje testów:
| Sekcja | Opis | Testów |
|--------|------|--------|
| A | DB/Schema — tabela offers istnieje (weryfikacja przez API) | 1 |
| B | CRUD — GET/POST/PATCH/DELETE + filtrowanie | 12 |
| C | PDF — Content-Type, rozmiar, 404 dla nieistniejącej | 4 |
| D | Validation — 422 bez title, 404 patch/delete, tender_id | 5 |
| E | UI Health — 3000/, 3000/demo, /docs, /health | 4 |
| F | Integration — e2e create+PDF, paginacja, auth guard | 6 |
| CLEANUP | Usunięcie ofert testowych | 1 |
| **RAZEM** | | **~33** |

### Oczekiwane nowe pliki

```
services/api/routers/offers.py              -- Agent 1
apps/ui/src/components/pages/OfertaPage.tsx -- Agent 2
```

---

## BAZY DANYCH — PEŁNA MAPA (stan: 07.07.2026)

### Statystyki bazy `terraos`
- **76 tabel** + 4 partycje `ht_*` + tabela `offers` (Faza 7)
- **10 Materialized Views**
- **250 indeksów**
- **PostgreSQL 16**, port 5432
- **pgvector** zainstalowany (`vector(1536)` na `ht_analysis`)

### Tabele rynkowe — DANE ZEWNĘTRZNE

| Tabela | Wierszy | Rozmiar | Opis |
|--------|---------|---------|------|
| `historical_tenders` | 1 403 436 | 1.2 GB | Przetargi BZP 2024-2025 (Atlas CC BY 4.0) |
| `icb_ceny_srednie` | 784 685 | 368 MB | Ceny Intercenbud 2008-2026 |
| `atlas_buyers` | ~45k | 24 MB | Zamawiający z Atlas |
| `atlas_contractors` | ~38k | 21 MB | Wykonawcy z Atlas |
| `sekocenbud_items` | 23 725 | 7 MB | Katalog Sekocenbud |
| `ddc_work_items` | ~1.5k | 4.5 MB | DDC CWICR KNR items |
| `intercenbud_regional_rates` | ~1k | 280 kB | Współczynniki regionalne ICB |
| `icb_narzuty` + `intercenbud_narzuty` | ~800 | ~220 kB | Narzuty ICB (Kp, Z, Kz) |

### Tabele aplikacyjne — TENANT (RLS)

| Tabela | Opis |
|--------|------|
| `tenant`, `organizations`, `users` | Multi-tenant core |
| `tender` | Aktywne przetargi z BZP feed (demo: 6 rekordów) |
| `estimate`, `estimate_line` | Kosztorysy z liniami |
| `rate_card` | Stawki jednostkowe per tenant |
| `przedmiar_item` | Pozycje przedmiaru (OCR/AI) |
| `kosztorys_items` | Pozycje kosztorysu |
| `historical_bids` | Historia ofert własnych (won/lost + margin) |
| `employee` | Pracownicy (85 rekordów) |
| `availability` | Dostępność zasobów (119 rekordów) |
| `contract` | Kontrakty (11 demo) |
| `tender_alert` | Alerty na nowe przetargi (RLS) |
| `tender_bookmark` | Pipeline kanban (RLS) |
| `competitor_watch` | Obserwowani konkurenci (RLS) |
| `buyer_crm` | CRM zamawiających (RLS) |
| `bid_intelligence` | Historia ofert z rank_position (RLS) |
| `offers` | **Oferty przetargowe z PDF export (Faza 7)** |

### Materialized Views

| MV | Opis | Odświeżanie |
|----|------|-------------|
| `mv_buyer_ranking` | Top zamawiający (budownictwo, ≥3 przetargi) | Ręczne |
| `mv_contractor_ranking` | Top wykonawcy (CPV2×region, win_rate) | Ręczne |
| `mv_market_trend` | Trendy rynkowe (kwartał×CPV3×region) | Ręczne |
| `mv_price_index` | Indeks cen ICB (kategoria×typ×kwartał) | Ręczne |
| `mv_tender_benchmark` | Benchmark przetargów (CPV5×region×kwartał) | Ręczne |
| `mv_competitor_recent_wins` | Wygrane przetargi (rolling 90d) | 24h po ingest |
| `mv_buyer_quarterly_spend` | Kwartalny spend per zamawiający×CPV5 | Co tydzień |
| `mv_regional_price_level` | Region×CPV5×kwartał: avg/median + ICB | Co tydzień |
| `mv_bid_win_analytics` | Win rate vs. narzut % per CPV5/region | 24h |
| `mv_labor_inflation_index` | Inflacja cen ICB: YoY + QoQ | Kwartalnie |

---

## ARCHITEKTURA — DECYZJE KLUCZOWE

### API

1. **Dual API versioning:** `/api/v1/` (CRUD aplikacyjny) + `/api/v2/` (analityczny/intelligence)
2. **RLS via JWT:** `SET app.current_tenant_id = '<uuid>'` przed każdym zapytaniem do tabel z RLS
3. **FTS konfiguracja `simple`:** brak lematyzacji polskiej -- do keyword search używać `ILIKE '%kw%'`, NIE `to_tsquery`
4. **Date range:** `date >= (SELECT max(date) - INTERVAL '365 days' FROM historical_tenders)` -- dane kończą się 2025-12-22
5. **Duplicate protection:** UNIQUE constraints na bookmark/alert/competitor/crm chroni przed race conditions

### UI

6. **Tailwind v4:** `@import "tailwindcss"` (NIE `@tailwind base`)
7. **motion/react:** NIE `framer-motion`
8. **AnimatePresence:** zawsze ternary `? : null` (NIE `&&`)
9. **API paths:** relative `/api/v1/...` (Caddy proxy) -- NIE absolutne localhost
10. **Odpowiedzi list:** `{items: [], total: N}` -- uwaga: niektóre endpointy mają inne shape (patrz PITFALLS)

### Dane

11. **contractor NIP coverage:** 32% -- ~50% przetargów ma `anon-XXXX` anonymized NIP (ograniczenie Atlas)
12. **bridge table `nuts_region_map`:** WYMAGANA dla relacji historical_tenders.province (NUTS) <-> intercenbud_regional_rates.voivodeship
13. **Brak FK między katalogami:** `sekocenbud_items` i `icb_ceny_srednie` -- łączy je `price_catalog_item`

### PITFALLS — Pułapki implementacyjne

| Problem | Szczegóły |
|---------|-----------|
| BuyerCRM response shape | `{tenders[], total_tenders_all_time}` NIE `{items, total}` |
| Notification field | `read` NIE `is_read` |
| OrgInvite field | `invited_by` NIE `status` |
| `expires_at` nullability | Zawsze używaj `?.` (może być null) |
| SQLAlchemy + UUID cast | Osobne queries dla `ht_id` (text) vs `tender_id` (uuid) -- brak `::uuid` w parametryzowanych |
| `mv_regional_price_level` | JOIN mismatch: format quarter + voivodeship (naprawiony w audycie Fazy 3) |

---

## FRAMEWORK PRACY

```
AUDIT --> AGENTS --> BUILD --> TEST --> DEBUG
  |           |       |         |         |
Read     Parallel  npm    pytest  Fix +
existing  agents   build  /tmp/   retest
files     (1-4)    0 err  test_*  OK
```

### Wzorzec dla nowej Fazy

1. **Audit:** Przeczytaj istniejące pliki + zidentyfikuj typy/hooki w `api-v2.ts`
2. **Agents:** Uruchom agentów równolegle (każdy = jeden moduł)
3. **Build:** `cd apps/ui && npm run build` -- cel: 0 błędów TS
4. **Test:** `python3 /tmp/test_faza7.py` -- cel: ALL PASS
5. **Debug:** Fix typów, null-safety, response shapes

---

## NASTĘPNE KROKI

### Faza 7 — do dokończenia

- [ ] Agent 1: Dostarczy `offers.py` -- CRUD + PDF endpoint + migracja DB (tabela `offers`)
- [ ] Agent 2: Dostarczy `OfertaPage.tsx` -- lista ofert, status, link do PDF, tworzenie
- [ ] Build check: `npm run build` -- 0 błędów TS
- [ ] Sidebar + demo/page.tsx: Dodać slot `oferta`
- [ ] Uruchomić testy: `python3 /tmp/test_faza7.py` -- cel ALL PASS

### Po Fazie 7

- [ ] Faza 8: Bidding Optimizer (AI scoring przetargów + rekomendacje)
- [ ] Faza 8: Historical Bids UI (analiza historii ofert własnych)
- [ ] Faza 9: PDF/DOCX export kosztorysów
- [ ] Faza 9: Integracja RFQ (zapytania do podwykonawców)

---

## KOMENDY TECHNICZNE

```bash
# Aktywacja środowiska
cd /home/ubuntu/terra-os
source .venv/bin/activate

# Testy API
python3 -m pytest tests/ -q --no-header
# Testy Fazy 7
python3 /tmp/test_faza7.py

# Build UI
cd apps/ui && npm run build

# Status serwisów
sudo systemctl status terra-api terra-ui

# Restart API po zmianach
sudo systemctl restart terra-api

# DB (hasło: terra_dev_2026)
PGPASSFILE=/tmp/.pgpass psql -h 127.0.0.1 -U terraos -d terraos
# lub
sudo -u postgres psql -d terraos

# Logi API
journalctl -u terra-api -f

# Refresh Materialized Views
sudo -u postgres psql -d terraos -c "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_market_trend;"
```

---

## ZASADY TECHNICZNE (KRYTYCZNE)

1. **Tailwind v4** -- `@import "tailwindcss"` (NIE `@tailwind base`)
2. **motion/react** -- NIE framer-motion
3. **AnimatePresence** -- zawsze ternary `? : null` (NIE `&&`)
4. **API paths:** relative `/api/v1/...` (Caddy proxy)
5. **Odpowiedzi list:** `{items: [], total: N}` (ale weryfikuj per endpoint!)
6. **PLN format:** `1 200 000 zł`
7. **Daty:** `DD.MM.YYYY`
8. **Język UI:** polski
9. **Dark theme:** zinc/slate palette, earth-* accents
10. **NIE em-dash** -- używaj `--` lub `-`
11. **UUID vs text:** `tender.id` = UUID, `historical_tenders.id` = text -- nie mieszaj bez casta
12. **RLS:** Zawsze ustawiaj `app.current_tenant_id` przed zapytaniami do tabel z RLS

---

*Dokument utrzymywany przez Agency Agents NEXUS -- Senior Developer*
*Następna aktualizacja: po zamknięciu Fazy 7*
