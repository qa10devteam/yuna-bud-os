# BudOS — Plan Wdrożenia

> Platforma dla firm budowlanych wygrywających przetargi publiczne.
> Trzy moduły: Zwiad Przetargowy · Silnik Decyzyjny AI · Kosztorys AI

---

## EPIKI

### EPIK 1 — Zwiad Przetargowy
Automatyczne monitorowanie portali BZP i TED, inteligentne dopasowanie przetargów do profilu firmy oraz system alertów. Cel: firma nie przegapi żadnego pasującego przetargu.

**Moduły:**
1. **Monitor BZP/TED** — scraping, parsowanie, normalizacja danych
2. **Matching AI** — scoring dopasowania do profilu CPV/regionu/wartości
3. **System Alertów** — email/push/webhook przy nowych trafieniach

---

### EPIK 2 — Silnik Decyzyjny AI
Analiza opłacalności przetargu: czy warto składać ofertę? Wielowymiarowy scoring, raporty PDF dla zarządu, historia decyzji.

**Moduły:**
4. **Analiza GO/NO-GO** — parser SWZ, wykrywanie red-flagów, scoring
5. **Raport Decyzyjny** — generowanie PDF z rekomendacją i uzasadnieniem
6. **Historia Decyzji** — track record, mierzenie skuteczności

---

### EPIK 3 — Kosztorys AI
Automatyczne generowanie wycen z dokumentacji przetargowej (SWZ, przedmiary, projekty), eksport do formatów branżowych.

**Moduły:**
7. **Parser Dokumentów** — OCR/ekstrakcja z PDF/DOCX, chunking
8. **Generator Kosztorysu** — LLM mapowanie na katalogi KNR/KSNR, wycena
9. **Eksport ATH/KNR** — generowanie plików kompatybilnych z Norma/Zuzia

---

## FEATURE MAP

### Moduł 1 — Monitor BZP/TED

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Scraping BZP (miniPortal/ezamawiajacy) | **P1** | Pobieranie nowych ogłoszeń co 4h, deduplicja po ID |
| Scraping TED (UE) | **P2** | Ogłoszenia unijne, filtr PL + kategorie budowlane |
| Normalizacja danych | **P1** | Mapowanie różnych formatów na wspólny model `Tender` |
| Filtr CPV | **P1** | Konfigurowalny zestaw kodów CPV dla firmy |
| Filtr geograficzny | **P2** | Województwa, promień od siedziby |
| Filtr wartości | **P2** | Min/max wartość zamówienia |
| Historia ogłoszeń | **P2** | Archiwum 24 miesięcy, wyszukiwarka fulltext |
| Webhook inbound (BZP API) | **P3** | Subskrypcja oficjalnego API BZP jeśli dostępne |

---

### Moduł 2 — Matching AI

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Profil firmy (CPV + region + wartość) | **P1** | Konfiguracja kryteriów dopasowania |
| Scoring 0–100 | **P1** | Ważona suma: CPV 40% + region 25% + wartość 20% + specjalizacja 15% |
| Wyjaśnienie score | **P1** | `match_reason` — 1–2 zdania dlaczego dobre dopasowanie |
| Uczenie ze zwrotek | **P2** | Firma akceptuje/odrzuca → fine-tuning wag |
| Podobne przetargi | **P2** | "Widziałeś też..." — embedding similarity |
| Profil kupującego | **P3** | Historia zamówień zamawiającego, preferencje |
| Konkurenci w przetargu | **P3** | Dane historyczne z wygranych przetargów TED |

---

### Moduł 3 — System Alertów

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Alert email (nowy przetarg) | **P1** | Digest dzienny / alert natychmiastowy konfigurowalny |
| Alert in-app (bell) | **P1** | Powiadomienia w topbarze, licznik nieprzeczytanych |
| Alert deadline | **P1** | -7dni / -3dni / -1dzień przed terminem składania |
| Webhook outbound | **P2** | POST do URL klienta (integracja z Slack/Teams) |
| Alert zmiany ogłoszenia | **P2** | Zamawiający zmienił SWZ — powiadom przypisanych |
| Push notification (PWA) | **P3** | Browser push dla zalogowanych użytkowników |
| Preferencje per użytkownik | **P2** | Każdy pracownik konfiguruje swoje kanały |

---

### Moduł 4 — Analiza GO/NO-GO

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Parser SWZ (PDF/DOCX) | **P1** | Ekstrakcja kluczowych wymagań: warunki, terminy, kary |
| Wykrywanie Red Flagów | **P1** | AI identyfikuje ryzyka: rażąco niskie ceny, nierealne terminy |
| Scoring GO/WARN/NO-GO | **P1** | Decyzja z progami konfigurowalnymi per firma |
| Analiza warunków udziału | **P1** | Spełniane/niespełniane wymagania formalne |
| Szacowanie ryzyka | **P2** | Kary umowne, ryzyko materiałowe, podwykonawcy |
| Porównanie z historią | **P2** | "Podobny przetarg wygraliście w 2023 z marżą X%" |
| Checklist ofertowy | **P2** | Auto-generowana lista dokumentów do złożenia |
| Analiza konkurencji | **P3** | Poprzedni zwycięzcy podobnych przetargów |

---

### Moduł 5 — Raport Decyzyjny

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Generowanie PDF | **P1** | Raport dla zarządu: streszczenie, score, rekomendacja |
| Szablon raportu | **P1** | Logo firmy, formatowanie branded |
| Executive Summary | **P1** | 1 strona: GO/NO-GO + 3 kluczowe argumenty |
| Sekcja ryzyk | **P1** | Tabela red flagów z poziomem severity |
| Sekcja finansowa | **P2** | Szacowany budżet, marża, próg rentowności |
| Eksport DOCX | **P2** | Edytowalny Word do dalszej pracy |
| Udostępnianie linkiem | **P2** | Tymczasowy URL read-only dla zewnętrznych |
| Historia raportów | **P3** | Repozytorium wygenerowanych raportów per przetarg |

---

### Moduł 6 — Historia Decyzji

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Zapis decyzji (GO/NO-GO + uzasadnienie) | **P1** | Każda decyzja logowana z datą i użytkownikiem |
| Wynik przetargu | **P1** | Wygrana/przegrana, wartość kontraktu |
| Dashboard skuteczności | **P2** | Win-rate, średnia marża, top-CPV |
| Analiza błędów | **P2** | Przegraने przetargi: co poszło nie tak |
| Eksport historii CSV | **P2** | Raportowanie dla zarządu |
| KPI tracking | **P3** | Cele kwartalne: X wygranych przetargów |

---

### Moduł 7 — Parser Dokumentów

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Upload PDF/DOCX | **P1** | Drag&drop, limit 50MB, queue asynchroniczny |
| OCR dla skanów | **P1** | Tesseract/Azure Vision dla dokumentów papierowych |
| Ekstrakcja tabel | **P1** | Przedmiary budowlane jako strukturyzowane dane |
| Chunking z metadanymi | **P1** | Page, section, type — potrzebne do RAG |
| Ekstrakcja pozycji kosztorysowych | **P1** | Nr KNR, opis, jednostka, ilość z dokumentów |
| Walidacja kompletności | **P2** | Czy wszystkie wymagane dokumenty zostały dostarczone |
| Re-parse po aktualizacji | **P2** | Ponowne przetworzenie gdy zamawiający zmienia SWZ |

---

### Moduł 8 — Generator Kosztorysu

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Mapowanie na katalogi KNR | **P1** | LLM mapuje opisy robót na pozycje KNR/KSNR |
| Automatyczna wycena | **P1** | Ceny z SEKOCENBUD / własne narzuty |
| Edytor kosztorysu | **P1** | Tabela z możliwością ręcznej korekty pozycji |
| Warianty A/B | **P1** | Agresywna vs. bezpieczna oferta cenowa |
| Obliczanie narzutów | **P2** | Konfigurowalny KP, Z, VAT per kontrakt |
| Walidacja budżetu | **P2** | Porównanie z szacunkową wartością zamawiającego |
| Historia wersji | **P2** | v1, v2, v3 — śledzenie zmian wyceny |
| Podsumowanie ryzyka cenowego | **P3** | Analiza wrażliwości na zmiany cen materiałów |

---

### Moduł 9 — Eksport ATH/KNR

| Feature | Priorytet | Opis |
|---------|-----------|------|
| Eksport ATH (Norma Pro) | **P1** | Format `.ath` kompatybilny z Norma Pro / Zuzia |
| Eksport KNR (CSV/XML) | **P1** | Standard branżowy dla kosztorysantów |
| Eksport PDF kosztorysu | **P1** | Formatowanie wg standardów budowlanych |
| Eksport XLSX | **P2** | Excel z formułami i tabelami zbiorczymi |
| Eksport do systemów ERP | **P3** | Integracja z SAP/Symfonia przez API |
| Podpis cyfrowy PDF | **P3** | Kwalifikowany podpis elektroniczny |

---

## KOLEJNOŚĆ WDROŻENIA

### Sprint 1 (tyg. 1–2) — Fundament i Zwiad v1
**Cel:** Pierwsza wartość dla użytkownika — lista przetargów w UI

**Backend:**
- [ ] Setup FastAPI + PostgreSQL + Redis
- [ ] Model danych `Tender` + migracje Alembic
- [ ] Scraper BZP (miniPortal) — cron co 4h
- [ ] Endpoint `GET /api/v2/tenders` z paginacją i filtrami

**Frontend:**
- [ ] Scaffold `src/lib/api.ts` — plain fetch functions
- [ ] Scaffold `src/types/tender.ts` — typy TypeScript
- [ ] Strona `/app/zwiad` — lista przetargów z filtrem status/score
- [ ] Komponent `TenderCard` — tytuł, buyer, deadline, score badge

**Definition of Done S1:**
- Lista przetargów ładuje się w < 2s
- Dane z BZP aktualizowane automatycznie
- TypeScript kompiluje bez błędów (`tsc --noEmit`)
- Deploy na staging

---

### Sprint 2 (tyg. 3–4) — Matching AI + Alerty
**Cel:** System inteligentnie filtruje przetargi pasujące do firmy

**Backend:**
- [ ] Moduł profilowania firmy (CPV, region, wartość)
- [ ] Serwis scoringu (GPT-4o / embeddingi OpenAI)
- [ ] Endpoint `GET /api/v2/tenders/{id}/match-score`
- [ ] Serwis alertów email (SendGrid)
- [ ] Cron alertów deadline (-7d/-3d/-1d)

**Frontend:**
- [ ] Strona `/app/zwiad/{id}` — detail view przetargu
- [ ] Badge GO/WARN/NO-GO na kartach
- [ ] Panel ustawień alertów
- [ ] In-app notification bell (dane real)

**Definition of Done S2:**
- Score pojawia się w < 5s od importu nowego przetargu
- Email alert wysłany w ciągu 10 min od nowego pasującego przetargu
- Win-rate matching ≥ 80% (test na historycznych danych)

---

### Sprint 3 (tyg. 5–6) — Parser + Analiza GO/NO-GO v1
**Cel:** Upload SWZ → automatyczna analiza ryzyka

**Backend:**
- [ ] Upload service (S3/MinIO)
- [ ] Parser PDF (pdfplumber + LangChain chunking)
- [ ] LLM pipeline: ekstrakcja wymagań + red flagów
- [ ] Endpoint `POST /api/v2/tenders/{id}/analyze`
- [ ] Endpoint `GET /api/v2/analysis/{tenderId}`
- [ ] Model `Analysis` + `RedFlag` w DB

**Frontend:**
- [ ] Upload dokumentów na stronie przetargu
- [ ] Strona `/app/silnik` — lista analiz
- [ ] Widok analizy: red flags, score, warunki udziału
- [ ] Loading states z progress bar (SSE lub polling)

**Definition of Done S3:**
- Analiza SWZ (10 stron) kończy się w < 60s
- Red flagi wykrywane z precyzją ≥ 75% (test na 20 przetargach)
- UI pokazuje status: `analyzing` → `ready`

---

### Sprint 4 (tyg. 7–8) — Raport PDF + Kosztorys v1
**Cel:** Zarząd dostaje raport; kosztorysant dostaje pierwszą wycenę

**Backend:**
- [ ] Generator PDF (WeasyPrint / Puppeteer)
- [ ] Endpoint `POST /api/v2/analysis/{id}/report`
- [ ] Parser przedmiarów (tabele z PDF/DOCX)
- [ ] Mapowanie KNR (LLM + katalog KNR embeddings)
- [ ] Endpoint `POST /api/v2/cost-estimates`
- [ ] Endpoint `GET /api/v2/cost-estimates/{id}`

**Frontend:**
- [ ] Przycisk "Generuj raport" + download PDF
- [ ] Strona `/app/kosztorys` — lista kosztorysów
- [ ] Edytor kosztorysu (tabela, edytowalne pozycje)
- [ ] Warianty A/B switcher

**Definition of Done S4:**
- Raport PDF gotowy w < 30s
- Kosztorys generuje ≥ 90% pozycji z dokumentu (bez pozycji manualnych)
- Eksport PDF kosztorysu działa

---

### Sprint 5 (tyg. 9–10) — Eksport ATH + Historia Decyzji
**Cel:** Integracja z narzędziami kosztorysantów + tracking wyników

**Backend:**
- [ ] Generator pliku ATH (Norma Pro format)
- [ ] Generator CSV/XML KNR
- [ ] Model `Decision` (go/warn/nogo + uzasadnienie + wynik)
- [ ] Endpoint `POST /api/v2/decisions`
- [ ] Endpoint `GET /api/v2/decisions` + analytics

**Frontend:**
- [ ] Export panel: ATH / KNR / PDF / XLSX
- [ ] Strona `/app/silnik/historia` — lista decyzji
- [ ] Dashboard skuteczności (win-rate, avg score)
- [ ] Formularz zapisywania decyzji + wyniku

**Definition of Done S5:**
- Plik ATH otwiera się poprawnie w Norma Pro
- Historia decyzji dostępna z filtrem dat i wyniku
- Dashboard KPI liczy win-rate poprawnie

---

### Sprint 6 (tyg. 11–12) — Hardening, UX, Production
**Cel:** System gotowy do wdrożenia produkcyjnego

**Backend:**
- [ ] Rate limiting + auth refresh tokens
- [ ] Monitoring (Sentry + Prometheus/Grafana)
- [ ] Backup bazy danych (automated daily)
- [ ] Scraper TED (UE) — ogłoszenia unijne
- [ ] Webhook outbound (Slack/Teams)
- [ ] Load test: 50 concurrent users

**Frontend:**
- [ ] Responsive mobile (sidebar hamburger)
- [ ] Skeleton loaders wszędzie
- [ ] Error boundaries + toast notifications
- [ ] PWA manifest + service worker
- [ ] Onboarding flow (setup profilu firmy)
- [ ] E2E tests (Playwright): happy path x3 modułów

**Definition of Done S6:**
- Lighthouse score ≥ 85 (performance)
- Zero krytycznych błędów TS / ESLint
- E2E testy zielone na CI
- Dokumentacja API (OpenAPI/Swagger)
- SLA 99.5% uptime (1-tygodniowy test)

---

## RYZYKA TECHNICZNE

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja |
|--------|-------------------|-------|-----------|
| BZP zmienia format XML bez ostrzeżenia | Wysokie | Wysoki | Monitoring schemy + alert na parse errors, testy regresji |
| LLM hallucynacje w kosztorysie | Wysokie | Krytyczny | Human-in-the-loop review, confidence score, podświetlanie niepewnych pozycji |
| Format ATH (Norma) — brak spec publicznej | Średnie | Wysoki | Inżynieria wsteczna + testy z prawdziwą Normą, fallback na CSV |
| Opóźnienie API OpenAI / limity | Średnie | Średni | Queue z retry, fallback na open-source LLM (llama3), caching wyników |
| Skanowane PDFs słaba jakość OCR | Wysokie | Średni | Preprocessing (contrast, deskew), Azure Document Intelligence jako fallback |
| RODO / dane przetargów unijnych | Niskie | Wysoki | Dane są publiczne; PII tylko użytkowników — szyfrowanie at rest, audit log |
| Skalowanie: 1000+ przetargów/dzień | Niskie | Średni | PostgreSQL partycjonowanie po dacie, async workers (Celery/RQ) |
| Vendor lock-in OpenAI | Niskie | Średni | Abstrakcja LLM adapter, testy z Anthropic/Mistral jako drop-in |

---

## DEFINICJA DONE (per sprint)

### Sprint 1 ✅ Done gdy:
- [ ] `GET /api/v2/tenders` zwraca dane (≥10 prawdziwych przetargów z BZP)
- [ ] UI `/app/zwiad` renderuje listę bez błędów JS
- [ ] `tsc --noEmit` → 0 błędów
- [ ] CI pipeline zielony (lint + build)

### Sprint 2 ✅ Done gdy:
- [ ] Nowy przetarg dostaje score w ciągu 5s od importu
- [ ] Email alert trafia na skrzynkę testową w < 10 min
- [ ] Detail view przetargu pokazuje score + reason
- [ ] Testy jednostkowe scoring: ≥ 5 przypadków

### Sprint 3 ✅ Done gdy:
- [ ] Upload PDF → analiza gotowa w < 60s
- [ ] Min. 3 red flagi wykryte poprawnie na testowym SWZ
- [ ] UI pokazuje `status: ready` po zakończeniu analizy
- [ ] Endpoint analizy udokumentowany w Swagger

### Sprint 4 ✅ Done gdy:
- [ ] PDF raportu pobiera się i otwiera poprawnie
- [ ] Kosztorys zawiera ≥ 10 pozycji dla testowego przedmiaru
- [ ] Edytor kosztorysu zapisuje zmiany bez utraty danych
- [ ] Testy integracyjne parsera: ≥ 3 różne formaty PDF

### Sprint 5 ✅ Done gdy:
- [ ] Plik `.ath` importuje się w Norma Pro bez błędów
- [ ] Historia decyzji: filtrowanie + sortowanie działa
- [ ] Win-rate liczony poprawnie (manual test z 10 wpisami)
- [ ] Export XLSX otwiera się w Excel/LibreOffice

### Sprint 6 ✅ Done gdy:
- [ ] Lighthouse Performance ≥ 85
- [ ] Playwright E2E: zwiad → analiza → kosztorys → eksport — zielone
- [ ] 0 błędów `tsc --noEmit` + 0 błędów ESLint (errors)
- [ ] README z instrukcją local dev + deploy
- [ ] Sentry skonfigurowany, test error widoczny w dashboardzie

---

*Ostatnia aktualizacja: Sprint 1 — dokument żyjący, aktualizuj po każdym sprint review.*
