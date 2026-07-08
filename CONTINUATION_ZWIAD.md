# TERRA.OS — KONTYNUACJA PRAC: Moduł Zwiad Fazy 1-20
## Data: 2026-07-08 | Sesja: TED connector + enrichment + health check

---

## STAN FAZ MODUŁU ZWIAD (Blok A — Discovery)

| # | Faza | Stan | Uwagi |
|---|------|------|-------|
| 1 | TED EU connector + normalizer | ✅ DONE | 569 TED w DB, BT-21-Lot titles, classification-cpv |
| 2 | TED: CPV + wartość z search API | ✅ DONE | real titles PL, classification-cpv |
| 3 | BZP dokumenty SIWZ | ❌ TODO | Router `bzp_documents.py` istnieje, sprawdzić live fetch + UI drawer |
| 4 | BZP ResultNotice (kto wygrał) | ✅ DONE | `fetch_result_notices()` + `sync_result_notices_to_historical_bids()` w bzp_connector.py |
| 5 | Historical tenders → main table | ✅ DONE | `scripts/migrate_historical_to_tender.py` — 500 rows migrated (5035 dostępnych CPV45%) |
| 6 | Cron systemd timer (BZP daily) | ✅ DONE | `terra-ingest.timer` 04:00 UTC, errors=0 |
| 7 | Cron TED tygodniowy | ✅ DONE | `terra-ingest-ted.timer` Sun 05:00 UTC, errors=0 |
| 8 | BIP connector | ❌ TODO | `source_kind='bip'` istnieje, brak implementacji |
| 9 | Deduplicator cross-source | ⚠️ PARTIAL | pg_trgm działa (1 para znaleziona), brak BZP↔TED fuzzy match po buyer+title |
| 10 | Geo enrichment (NUTS/TERC) | ❌ TODO | TED: 569 bez voivodeship; potrzeba NUTS→voivodeship mapping |
| 11 | ZwiadPage — filtr po źródle | ✅ DONE | Source dropdown: bzp/ted/bip |
| 12 | ZwiadPage — filtr po CPV | ✅ DONE | CPV prefix search (4511→536, 45111200→103) |
| 13 | ZwiadPage — filtr po wartości | ✅ DONE | min_value/max_value (min 500k→361 wyników) |
| 14 | ZwiadPage — filtr po voivodeship | ✅ DONE | ILIKE z diacritics (śląskie→497) |
| 15 | ZwiadPage — sorting | ✅ DONE | match_score/deadline/value/published |
| 16 | Scoring v2 — wagi konfigurowalne | ❌ TODO | Scorer hardcoded; dodać tenant-level config (tabela `scoring_config`) |
| 17 | Scorer — deadline proximity bonus | ❌ TODO | Przetargi z bliskim deadline powinny mieć boost |
| 18 | Scorer — historical win rate CPV | ❌ TODO | Jeśli tenant wygrywał w CPV X → boost |
| 19 | Alert email — nowe przetargi | ❌ TODO | `tender_alert` tabela istnieje, brak email dispatch |
| 20 | Health check źródeł | ✅ DONE | `/api/v1/sources/health` — BZP OK, TED OK |
| 21 | Dashboard — real tender total | ✅ DONE | `api.ts` używa `json.total` zamiast `tenders.length` |
| 22 | MarketIntelPage — seasonality tab | ✅ DONE | `useSeasonality` hook + `SeasonalityChart` komponent |
| 23 | MarketBar — poll throttle | ✅ DONE | 60s → 300s (12 req/h zamiast 60) |
| 25 | BZP multi-page AM/PM split | ✅ DONE | pageSize=500, 1075 BZP w DB |

---

## AKTUALNY STAN DANYCH (DB)

```
terraos=> SELECT source, COUNT(*), ROUND(AVG(match_score)::numeric,3) FROM tender
           WHERE tenant_id='ec3d1e16-2139-48c2-93b5-ffe0defd606d' GROUP BY source;

 source | count | avg_score
--------+-------+-----------
 bzp    |  1109 |     0.478
 ted    |  1015 |     0.406
 TOTAL  |  2124 |
```

- **BZP:** 1109 przetargów, 2026-06-08 → 2026-07-08, pełne tytuły + CPV + voivodeship + wartość
- **TED:** 1015 przetargów, polskie tytuły (BT-21-Lot), CPV (classification-cpv), 12% ma wartość
- **Cron:** BZP daily 04:00 UTC (`days_back=2`), TED weekly Sunday 05:00 UTC (`days_back=7`)

---

## SERWISY

| Serwis | Status | Adres |
|--------|--------|-------|
| terra-api | ✅ active | http://localhost:8000 (systemd) |
| terra-ui | ✅ active | http://localhost:3000 (systemd) |
| terra-ingest.timer | ✅ enabled | Daily 04:00 UTC (BZP+TED) |
| terra-ingest-ted.timer | ✅ enabled | Sunday 05:00 UTC (TED 7d) |
| PostgreSQL | ✅ active | port 5432, db=terraos, user=terraos |
| Vercel | ⚠️ BLOCKED | Token wygasł, potrzeba `vercel login` |

---

## KLUCZOWE PLIKI (zmienione w tej sesji)

```
services/ingestion/ted_connector.py     — TED v3 API connector, fields: BT-21-Lot, classification-cpv, estimated-value-lot
services/ingestion/normalize.py         — normalize_ted_notice() z BT-21-Lot/Part/BT-24-Lot
services/ingestion/scorer.py            — fix DivisionByZero (value_pln <= 0)
services/ingestion/pipeline.py          — include_ted=True, run_ingest() obsługuje BZP+TED
scripts/daily_ingest.py                 — INGEST_INCLUDE_TED env var, INGEST_DAYS_BACK
services/api/services/api/routers/sources_health.py  — /api/v1/sources/health endpoint (NEW)
services/api/services/api/main.py       — sources_health router registered
/etc/systemd/system/terra-ingest-ted.service  — TED weekly ingest
/etc/systemd/system/terra-ingest-ted.timer    — Sunday 05:00 UTC
```

---

## TED API — ODKRYCIA (ważne dla kontynuacji)

### Poprawne field names TED v3 (walidowane 2026-07-08)
```
BT-21-Lot              — tytuł przetargu (multilingual dict: {"pol": ["..."]})
BT-21-Part             — tytuł na poziomie Part (fallback)
BT-24-Lot              — opis lotu
BT-300-Lot             — dodatkowy opis
classification-cpv     — lista kodów 8-cyfrowych ["45000000", "45233142"]
estimated-value-lot    — lista wartości ["48222878.37"]
estimated-value-cur-lot — waluta ["PLN"]
organisation-name-buyer — {"pol": ["Gmina X"]}
organisation-city-buyer — ["Warszawa"]
deadline-receipt-tender-date-lot — ["2026-07-31+02:00"]
place-performance-streetline1-part — adres realizacji
place-of-performance-post-code-part — kod pocztowy
publication-number     — "449219-2026"
publication-date       — "2026-07-01+02:00"
```

### TED API endpoint
```
POST https://api.ted.europa.eu/v3/notices/search
Body: {"query": "organisation-country-buyer=POL AND contract-nature=works AND publication-date>=YYYYMMDD AND publication-date<=YYYYMMDD", "fields": [...], "limit": 100, "page": N}
Auth: BRAK (publiczne)
Paginacja: page=1,2,3... (max ~100 per page)
```

### TED XML (per-notice enrichment — NIE zaimplementowane)
```
GET https://ted.europa.eu/en/notice/{pub_num}/xml
Tytuł w: <cbc:Name languageID="POL">...</cbc:Name>
NUTS w: <cbc:CountrySubentityCode listName="nuts">PL911</cbc:CountrySubentityCode>
```

---

## CO ZROBIĆ DALEJ (priorytet)

### Fazy szybkie (UI filtry: 11-15) — jeden batch
1. ZwiadPage.tsx — dodaj filtry: source dropdown, CPV input, value range, voivodeship, sort
2. API endpoint `/api/v1/tenders` — obsłuż query params: `?source=ted&cpv=45&min_value=1000000&voivodeship=mazowieckie&sort=deadline`

### Fazy backendowe (3-5, 8-9)
3. **Faza 3** — `bzp_documents.py` już istnieje; sprawdź czy fetch działa live, dodaj UI drawer
4. **Faza 4** — BZP ResultNotice: `NoticeType=ResultNotice`, zapisz winner/value do `historical_bids`
5. **Faza 5** — `scripts/migrate_historical_to_tender.py`: SELECT z `historical_tenders` WHERE Works AND date >= 90d → upsert do `tender`
6. **Faza 8** — BIP: znaleźć publiczne BIP API przetargów budowlanych
7. **Faza 9** — Deduplicator: matching po buyer+title+deadline (fuzzy) cross BZP/TED

### Fazy scoring (16-18)
8. Konfigurowalne wagi scorera per tenant (tabela `scoring_config`)
9. Deadline proximity bonus
10. Historical win rate boost

### Faza 19 — Email alert
11. Dispatch email (himalaya/SMTP) gdy nowy przetarg match_score > threshold

### Deploy
12. **Vercel token** — `vercel login` lub podaj VERCEL_TOKEN env var

---

## KOMENDY STARTOWE

```bash
cd /home/ubuntu/terra-os && source .venv/bin/activate

# Status
sudo systemctl status terra-api terra-ui
sudo systemctl list-timers terra-ingest* --no-pager
curl -s http://localhost:8000/api/v1/sources/health | python3 -m json.tool

# DB
sudo -u postgres psql -d terraos -c "SELECT source, COUNT(*) FROM tender WHERE tenant_id='ec3d1e16-2139-48c2-93b5-ffe0defd606d' GROUP BY source;"

# Pełny ingest (30 dni)
sudo systemd-run --wait --uid=ubuntu \
  --property=Environment="$(sudo systemctl show terra-ingest --property=Environment | sed 's/^Environment=//' | sed 's/INGEST_DAYS_BACK=2/INGEST_DAYS_BACK=30/')" \
  --property=WorkingDirectory=/home/ubuntu/terra-os \
  /home/ubuntu/terra-os/.venv/bin/python3 /home/ubuntu/terra-os/scripts/daily_ingest.py

# Restart API
sudo systemctl restart terra-api

# Plan faz (pełny opis)
cat /home/ubuntu/terra-os/.hermes/plans/2026-07-08_zwiad-discovery-fixes.md
```

---

## INSTRUKCJA DLA NOWEGO WĄTKU

```
cat /home/ubuntu/terra-os/CONTINUATION_ZWIAD.md

Kontynuuj fazy 3-19 modułu Zwiad. Auto-mode: wdrażaj bez pytania.
Priorytet: fazy 11-15 (UI filtry), potem 3-5 (backend), potem 16-19 (scoring+alerts).
```

---

*Ostatnia aktualizacja: 2026-07-08 10:45 UTC*
