# Terra.OS — Prawdziwe Dane: Status Weryfikacji

**Data weryfikacji:** 2026-07-07  
**Status:** ✅ Wszystkie źródła przetestowane live, dane w PostgreSQL

---

## TL;DR — Co mamy, co nie

| Źródło | Status | Dane w DB | Uwaga |
|--------|--------|-----------|-------|
| **Atlas Przetargów API** | ✅ LIVE | `historical_tenders` 552 rows (sample) | REST API działa, 1.4M rekordów |
| **DDC CWICR PL_WARSAW** | ✅ POBRANE | `ddc_work_items` 10k rows | Parquet 25MB, 55 719 pozycji KNR |
| **GUS BDL API** | ✅ LIVE | `gus_construction_index` 100 rows | 2 zmienne, 5 lat, 10 województw |
| **INTERCENBUD/SEKOCENBUD** | ❌ BRAK | — | Płatne, wymaga kontaktu z Athenasoft |
| **KNR normatywy** | ⚠️ PARTIAL | DDC zastępuje KNR | DDC ma MasterFormat, nie KNR numery |
| **BZP API** | ✅ LIVE | — | ezamowienia.gov.pl/mo-board/api/v1 |
| **Friedman/NGBoost modele** | ⚠️ STUB | — | Trenowane na mock data, nie real |

---

## 1. Atlas Przetargów API

**URL:** `https://atlasprzetargow.pl/api/`  
**Typ:** REST, publiczny (bez klucza), CC BY  
**Rozmiar:** 1.4M rekordów (CPV 45: 666 683 rekordów budowlanych)

### Endpoints
```
GET /api/tenders                        # lista przetargów
GET /api/tenders/agg/category-stats     # agregaty per CPV
GET /api/tenders/agg/province-stats     # per województwo
GET /api/buyers/{slug}                  # profil zamawiającego
GET /api/contractors/{slug}             # profil wykonawcy
GET /api/tenders/{id}                   # szczegóły
```

### Query params (tenders)
- `cpv` — kod CPV (np. `45000000`)
- `noticeType` — `TenderResultNotice`, `ContractNotice`, `ContractPerformingNotice`
- `orderType` — `Roboty budowlane`, `Dostawy`, `Usługi`
- `province` — NUTS-2 (np. `PL22`)
- `limit`, `page`
- `dateFrom`, `dateTo`

### Schema (CSV/API)
```
id, source, notice_type, tender_type, order_type, title, buyer, buyer_nip,
city, province, latitude, longitude, cpv_code, date,
estimated_value (PLN), currency, deposit_amount,
offers_count, contractor_name, contractor_city, contractor_province,
procedure_result, notice_url, bzp_number, ted_number
```

### Statystyki (CPV 45, 2024 live)
- `avg_offers_count` = 3.8
- `avg_value` = 8.7M PLN
- `median_value` = 476k PLN
- `count_period` = 37 105 (ostatnie 90 dni)
- `count_total` = 666 683

### Plik CSV release (bulk)
- Release: `v2026.Q2`
- File: `tenders_2024.csv.gz` (w toku download)
- Format: gzip CSV z 43 kolumnami
- Przykładowe rekordy: id=`2024/BZP 00000001...`

### DB Table
```sql
historical_tenders (
  id TEXT PK, source, notice_type, tender_type, order_type, title,
  buyer, buyer_nip, city, province, latitude, longitude, cpv_code,
  date DATE, estimated_value FLOAT, offers_count FLOAT,
  contractor_name, procedure_result, ...
)
```

---

## 2. DDC CWICR PL_WARSAW

**Repo:** `datadrivenconstruction/OpenConstructionEstimate-DDC-CWICR`  
**Licencja:** CC BY 4.0 (FREE)  
**Plik PL:** `PL___DDC_CWICR/PL_WARSAW_workitems_costs_resources_DDC_CWICR.parquet`  
**Lokalnie:** `/home/ubuntu/terra-os/data/ddc_cwicr_pl_warsaw_workitems.parquet`

### Co to jest
DDC CWICR to **baza pozycji kosztorysowych** z cenami materiałów, robocizny i sprzętu. NIE jest to katalog KNR (polskie normatywy SEKOCENBUD). Jest to odpowiednik KNR oparty na danych historycznych Warsaw + MasterFormat mapping.

### Rozmiar
- 900 225 wierszy total (wszystkie typy)
- 55 719 unikalnych pozycji (`rate_code`)
- 185 203 wiersze `row_type = Zakres prac` (scope items)

### Kolumny kluczowe (93 total)
```
rate_code              — unikalny kod pozycji
rate_final_name        — nazwa (po polsku)
rate_unit              — jednostka (m2, m3, szt, etc.)
row_type               — 'Zakres prac' | 'Zasób' | 'Operator maszyn' | ...
department_name        — kategoria robót
section_name           — podkategoria
total_cost_per_position — koszt całkowity (PLN per jednostkę)
total_material_cost_per_position — koszt materiałów
labor_hours_construction_workers — roboczogodziny
masterformat_division  — MasterFormat (np. '31 00 00' = Earthwork)
masterformat_section_title — tytuł sekcji
resource_name          — materiał/zasób
resource_price_per_unit_current — cena materiału (PLN/jed)
currency               — PLN
price_region           — PL_WARSAW
```

### Statystyki cen
- Zakres: 1 PLN — 25.7M PLN per jednostkę
- Mediana: ~6 000 PLN per jednostkę

### Jednostki (top)
- Sztuka: 14 139
- 100 m3: 5 475
- 100 m: 4 725
- 100 m2: 4 477

### WAŻNE - Ograniczenia
- Dane Warsaw-specific, nie ogólnopolskie
- Brak bezpośredniego mapowania KNR numerów (np. KNR 2-01 0101-01)
- MasterFormat zamiast KNR → wymaga cross-mapowania dla polskich SWZ
- Brak dat aktualizacji cen (prawdopodobnie 2024/2025)

### Qdrant Embeddings
- `PL_WARSAW_workitems_costs_resources_EMBEDDINGS_3072_DDC_CWICR.snapshot` — 3072-dim embeddings (snapshot Qdrant)
- `PL_WARSAW_workitems_costs_resources_EMBEDDINGS_BGEM3_V3_DDC_CWICR.snapshot` — BGE-M3 embeddings
- Do załadowania: `qdrant snapshot restore <file>`

### DB Table
```sql
ddc_work_items (
  rate_code, rate_final_name, rate_unit, row_type,
  department_name, section_name, total_cost_per_position FLOAT,
  total_material_cost_per_position FLOAT, labor_hours_construction_workers FLOAT,
  resource_name, resource_price_per_unit_current FLOAT,
  masterformat_division, masterformat_section_title,
  labor_class, currency, price_region
)
-- 10 000 rows załadowane (sample ze scope items)
```

---

## 3. GUS BDL API

**URL:** `https://bdl.stat.gov.pl/api/v1/`  
**Typ:** REST, publiczny (bez klucza), NUTS-2 granularność  
**Dokumentacja:** https://bdl.stat.gov.pl/bdl/start

### Dostępne zmienne budowlane
```
var 1548721 — Roboty budowlano-montażowe wg miejsca wykonywania (mln PLN)
  lata: 2020-2024, 10 województw, avg 2024 = 67 570 mln PLN

var 152349  — Produkcja budowlano-montażowa per mieszkaniec (PLN)
  lata: 2020-2024, 10 województw, avg 2024 = 8 645 PLN
```

### Hierarchia subject
```
K12 (PRZEMYSŁ I BUDOWNICTWO)
  → G225 (Produkcja budowlano-montażowa)
     → P2422 (sprzedaż wg PKD2007)
        → var 1548721 (wartość robót, mln PLN)
        → var 152349  (per mieszkaniec, PLN)
```

### API endpoint
```
GET /api/v1/data/by-variable/{var_id}?year=2024&pageSize=200
→ { results: [ {id, name, values: [{year, val}, ...]} ] }
```

### DB Table
```sql
gus_construction_index (
  variable_id TEXT, variable_name TEXT, unit_name TEXT, unit_id TEXT,
  year INTEGER, val FLOAT, measure_unit TEXT
)
-- 100 rows: 2 zmienne × 5 lat × 10 jednostek terytorialnych
```

### Trending 2020-2024
- 2020: 43 564 mln PLN → 2024: 67 570 mln PLN
- CAGR ≈ +11.6%/rok (realnie ~6-7% po odliczeniu inflacji)

---

## 4. BZP / eZamówienia API

**URL:** `https://ezamowienia.gov.pl/mo-board/api/v1/`  
**Status:** ✅ Live (testowane 2026-07-07)

### Działające endpoints
```
GET /notice?PageSize=N&NoticeType=X&PublicationDateFrom=YYYY-MM-DD
NoticeType values: (do weryfikacji z docs — ZP400PodProg jest BŁĘDNY)
Zwraca JSON z polami errors/type/title/status gdy błąd
```

### Uwaga
BZP API wymaga prawidłowych wartości `NoticeType`. Atlas Przetargów pokrywa BZP dane — preferuj Atlas REST API zamiast bezpośredniego BZP (Atlas ma agregaty, dedupe i normalizację).

---

## 5. Czego NADAL nie mamy

### INTERCENBUD / SEKOCENBUD
- Płatne subskrypcje (kwartalne)
- Athenasoft: brak kontaktu, brak próbek
- SEKOCENBUD RMS: 50 000+ pozycji KNR, format MDB/DBF
- **Ryzyko:** bez tego nie mamy polskich numerów KNR (KNR 2-01, etc.)
- **Workaround:** DDC CWICR jako proxy + MasterFormat mapping

### Friedman/NGBoost modele
- Trenowane na `stub_data` w `apps/estimation/`
- Nie załadowano `historical_tenders` do treningu
- Potrzebne: min. 1 000 rekordów z `cpv_code` + `estimated_value` + `province`

### Qdrant lokalny
- Snapshot DDC istnieje w repo, nie zainstalowany lokalnie
- Potrzebne: `docker run qdrant/qdrant` + restore snapshot
- Bez tego: brak semantic search po pozycjach KNR

### Ceny rynkowe 2024/2025
- DDC ma ceny Warsaw-only
- Brak danych z SEKOCENBUD, brak próbek ORGBUD/INTERCENBUD
- GUS BDL daje indeksy (%, mln PLN), nie ceny jednostkowe

---

## Następne kroki (priorytet)

1. **[TERAZ]** Załaduj pełny `tenders_2024.csv.gz` do `historical_tenders` (bulk)
2. **[TERAZ]** Uruchom Qdrant docker + restore DDC snapshot
3. **[WKRÓTCE]** Przetrenuj NGBoost na `historical_tenders` (CPV 45x, n>1000)
4. **[WKRÓTCE]** Pobierz pozostałe lata Atlas: 2022, 2023, 2025
5. **[DO NEGOCJACJI]** Kontakt Athenasoft → próbka INTERCENBUD
