# TERRA.OS — ROADMAP UI
## 3 Milestony × 20 Faz × 5 Sprintów = 300 tasków
*Wygenerowano: 2026-07-10 | Kontekst: M1–M4 backend done (commit 7a95763)*

---

## LEGENDA
- **Sprint** = 1 dzień pracy (jednostka atomowa, 1 commit)
- **Faza** = 5 sprintów (1 tydzień) — 1 strona lub podsystem UI
- **Milestone** = 20 faz (4 tygodnie) — 1 blok produktowy
- Status: `⬜ TODO` / `🔄 IN_PROGRESS` / `✅ DONE`

---

---

# MILESTONE 5 — ZDOBYWANIE KONTRAKTÓW (Sekcja 1)
*Cel: Wszystkie strony z bloku "Zdobywanie kontraktów" działają produkcyjnie z prawdziwymi danymi*

---

## FAZA 5.01 — ZwiadPage: filtry + tabela live
*Strona: ZwiadPage.tsx (1720 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.01.1 | Podłącz `GET /api/v2/tenders` do tabeli — paginacja cursor-based, 25/strona | ⬜ |
| S2 | 5.01.2 | Filtry: CPV prefix, voivodeship, min/max value, source dropdown — query params | ⬜ |
| S3 | 5.01.3 | Sortowanie klikalne (deadline / wartość / match_score / published_at) | ⬜ |
| S4 | 5.01.4 | Skeleton loader + empty state + error boundary | ⬜ |
| S5 | 5.01.5 | URL persistence filtrów (searchParams) + reset button | ⬜ |

## FAZA 5.02 — ZwiadPage: TenderDetail drawer
*Strona: TenderDetail.tsx (istniejący komponent)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.02.1 | Otwieranie drawera po kliknięciu wiersza — `GET /api/v2/tenders/{id}` | ⬜ |
| S2 | 5.02.2 | Tab "Szczegóły": tytuł, zamawiający, CPV, wartość, deadline, voivodeship | ⬜ |
| S3 | 5.02.3 | Tab "Dokumenty": lista z `GET /api/v2/bzp/documents/{id}` + pobieranie | ⬜ |
| S4 | 5.02.4 | Tab "Historia": historical_bids dla CPV — kto wygrywał, po ile | ⬜ |
| S5 | 5.02.5 | Akcje: Dodaj do pipeline / Zakładka / Eksport PDF | ⬜ |

## FAZA 5.03 — PipelinePage: Kanban board
*Strona: PipelinePage.tsx (344 linii, stub)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.03.1 | Pobierz tendery z `pipeline_status` != NULL — grupuj po statusie | ⬜ |
| S2 | 5.03.2 | Kanban: kolumny OBSERWOWANY / ANALIZOWANY / DECYZJA / OFERTA / ZŁOŻONY / WON/LOST | ⬜ |
| S3 | 5.03.3 | Drag & drop kart (dnd-kit) — PATCH `/api/v2/tenders/{id}` pipeline_status | ⬜ |
| S4 | 5.03.4 | Karta: tytuł, zamawiający, deadline countdown, wartość, match_score badge | ⬜ |
| S5 | 5.03.5 | Filtry pipeline: moje / zespołu / deadline < 7d / wartość > X | ⬜ |

## FAZA 5.04 — PipelinePage: timeline i metryki
*Strona: PipelinePage.tsx (rozbudowa)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.04.1 | Header KPI: pipeline_value, win_rate MTD, avg_deal_size, aktywne przetargi | ⬜ |
| S2 | 5.04.2 | Timeline view: oś czasu deadline dla aktywnych przetargów (SVG/recharts) | ⬜ |
| S3 | 5.04.3 | Velocity chart: tendery wchodzące vs kończące się w pipeline (ostatnie 30d) | ⬜ |
| S4 | 5.04.4 | Quick-add: dodaj przetarg do pipeline z Zwiad bez otwierania drawera | ⬜ |
| S5 | 5.04.5 | Eksport pipeline do CSV / XLSX | ⬜ |

## FAZA 5.05 — SilnikPage: AI scoring live
*Strona: SilnikPage.tsx (446 linii, stub)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.05.1 | Pobierz scoring_config z `GET /api/v2/scoring/config` — formularz edycji wag | ⬜ |
| S2 | 5.05.2 | Zapisz wagi `PUT /api/v2/scoring/config` + trigger recalculate | ⬜ |
| S3 | 5.05.3 | Score breakdown dla wybranego przetargu: waterfall chart (SensitivityWaterfall) | ⬜ |
| S4 | 5.05.4 | Top-10 przetargów według match_score — live preview po zmianie wag | ⬜ |
| S5 | 5.05.5 | Historia zmian wag (audit log) — tabela z timestampami | ⬜ |

## FAZA 5.06 — SilnikPage: deadline bonus + CPV win-rate
*Nowe features backendowe + UI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.06.1 | Backend: deadline proximity bonus w scorer.py (dni do deadline → boost 0–20%) | ⬜ |
| S2 | 5.06.2 | Backend: CPV win-rate boost — historical_bids → win_rate per CPV-4 | ⬜ |
| S3 | 5.06.3 | UI: Silnik — zakładka "Deadline Bonus" — wykres boost vs dni_do_deadline | ⬜ |
| S4 | 5.06.4 | UI: Silnik — zakładka "CPV Win-Rate" — heatmap CPV × win_rate | ⬜ |
| S5 | 5.06.5 | Testy: scorer v3 — recalculate 2124 tenderów, diff z v2 | ⬜ |

## FAZA 5.07 — DecyzjaPage: rekomendacje AI
*Strona: DecyzjaPage.tsx (354 linii, stub)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.07.1 | Lista przetargów z wysokim score (>0.7) wymagających decyzji | ⬜ |
| S2 | 5.07.2 | Karta decyzji: pros/cons AI-generated (POST /api/v2/ai/decision-brief) | ⬜ |
| S3 | 5.07.3 | Przycisk GO/NO-GO → PATCH pipeline_status + audit_log entry | ⬜ |
| S4 | 5.07.4 | Decision brief: ryzyko (WinProbGauge), szacowana marża, konkurencja | ⬜ |
| S5 | 5.07.5 | Historia decyzji — tabela GO/NO-GO z uzasadnieniami | ⬜ |

## FAZA 5.08 — DecyzjaPage: AHP + ryzyko
*Strona: AnalyticsPage.tsx — przenieś/rozszerz AHP*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.08.1 | Macierz AHP: pobierz kryteria z scoring_config, renderuj matrix input | ⬜ |
| S2 | 5.08.2 | Oblicz consistency ratio (CR) — wyświetl ostrzeżenie jeśli CR > 0.1 | ⬜ |
| S3 | 5.08.3 | RiskChart: ryzyko wykonania (harmonogram / finansowe / techniczne) | ⬜ |
| S4 | 5.08.4 | Sensitivity waterfall: jak zmiana każdego kryterium wpływa na wynik | ⬜ |
| S5 | 5.08.5 | Eksport decision brief do PDF (html2canvas / puppeteer endpoint) | ⬜ |

## FAZA 5.09 — BookmarksBoardPage: alerty + kanban
*Strona: BookmarksBoardPage.tsx (615 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.09.1 | Pobierz zakładki z `GET /api/v2/tenders?bookmarked=true` | ⬜ |
| S2 | 5.09.2 | Kanban zakładek: OBSERWUJ / PRIORYTET / ARCHIWUM — drag & drop | ⬜ |
| S3 | 5.09.3 | Alert config: dodaj/edytuj/usuń alerty email `POST /api/v2/alerts` | ⬜ |
| S4 | 5.09.4 | Alerty: lista aktywnych alertów + last_triggered + match_count | ⬜ |
| S5 | 5.09.5 | Test alert: "Testuj teraz" → `/api/v2/alerts/{id}/test` | ⬜ |

## FAZA 5.10 — NotificationsPage: centrum powiadomień
*Strona: NotificationsPage.tsx (497 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.10.1 | Pobierz powiadomienia z `GET /api/v2/notifications` — lista z paginacją | ⬜ |
| S2 | 5.10.2 | Mark as read — PATCH `/api/v2/notifications/{id}` | ⬜ |
| S3 | 5.10.3 | Filtry: typ (alert/system/tender), przeczytane/nieprzeczytane | ⬜ |
| S4 | 5.10.4 | NotificationsBell badge — real-time count (polling 30s) | ⬜ |
| S5 | 5.10.5 | Ustawienia powiadomień: email/in-app toggle per typ zdarzenia | ⬜ |

## FAZA 5.11 — BuyerCRMPage: zamawiający
*Strona: BuyerCRMPage.tsx (1212 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.11.1 | Tabela zamawiających — aggregate z tender.buyer_name, liczba przetargów | ⬜ |
| S2 | 5.11.2 | Profil zamawiającego: historia przetargów, CPV mix, average value | ⬜ |
| S3 | 5.11.3 | Notatki per zamawiający — POST/GET /api/v2/crm/buyers/{id}/notes | ⬜ |
| S4 | 5.11.4 | Kontakty: dodaj osobę kontaktową, email, telefon, stanowisko | ⬜ |
| S5 | 5.11.5 | Mapa zamawiających: PolandHeatmap kolorowana liczbą przetargów | ⬜ |

## FAZA 5.12 — CompetitorPage: analiza konkurencji
*Strona: CompetitorPage.tsx (511 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.12.1 | Lista konkurentów z historical_bids.winner_name — aggregate po firmach | ⬜ |
| S2 | 5.12.2 | Profil konkurenta: CPV mix, win_rate, avg cena, voivodeship coverage | ⬜ |
| S3 | 5.12.3 | Head-to-head: my org vs competitor — tabela wspólnych przetargów | ⬜ |
| S4 | 5.12.4 | Trendy: competitor win_rate month-over-month (recharts LineChart) | ⬜ |
| S5 | 5.12.5 | Alert: śledź konkurenta — powiadom gdy wygra > X przetargów w miesiącu | ⬜ |

## FAZA 5.13 — MarketIntelPage: rynek i trendy
*Strona: MarketIntelPage.tsx (749 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.13.1 | Podłącz `GET /api/v2/market/summary` — total value, count, avg CPV | ⬜ |
| S2 | 5.13.2 | Sezonowość: SeasonalityChart — przetargi per miesiąc (12 miesięcy) | ⬜ |
| S3 | 5.13.3 | CPV breakdown: top-20 CPV-4 per wartość — bar chart + tabela | ⬜ |
| S4 | 5.13.4 | Heatmapa regionalna: PolandHeatmap wg wartości przetargów per woj. | ⬜ |
| S5 | 5.13.5 | ICB Price Explorer: podłącz ICBPriceExplorer do realnych danych | ⬜ |

## FAZA 5.14 — MarketIntelPage: benchmarki i prognozy
*Strona: MarketIntelPage.tsx (cd)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.14.1 | Benchmark: moja win_rate vs rynek (per CPV) | ⬜ |
| S2 | 5.14.2 | Prognoza przetargów na kolejne 30/60/90 dni (na podstawie historii) | ⬜ |
| S3 | 5.14.3 | Market share: top-10 zamawiających per woj. — treemap | ⬜ |
| S4 | 5.14.4 | Eksport raportu rynkowego do PDF | ⬜ |
| S5 | 5.14.5 | Cache invalidation: `GET /api/v2/market/summary` — stale-while-revalidate | ⬜ |

## FAZA 5.15 — DashboardPage: panel główny live
*Strona: DashboardPage.tsx (468 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.15.1 | KPI cards: aktywne przetargi / pipeline value / alerty / win_rate | ⬜ |
| S2 | 5.15.2 | Ostatnie 5 przetargów z wysokim score — "Najgorętsze dziś" | ⬜ |
| S3 | 5.15.3 | Activity feed: ostatnie zdarzenia (nowy przetarg, zmiana statusu, alert) | ⬜ |
| S4 | 5.15.4 | Quick actions: Nowy alert / Dodaj przetarg / Otwórz Pipeline | ⬜ |
| S5 | 5.15.5 | Responsive: mobile-first dashboard (grid → single column na <768px) | ⬜ |

## FAZA 5.16 — SettingsPage: organizacja i profil
*Strona: SettingsPage.tsx (1203 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.16.1 | Profil organizacji: GET/PATCH `/api/v2/org` — nazwa, NIP, logo upload | ⬜ |
| S2 | 5.16.2 | Profil użytkownika: email, hasło (change password flow) | ⬜ |
| S3 | 5.16.3 | CPV preferowane: multi-select zapisz do scoring_config | ⬜ |
| S4 | 5.16.4 | Integracje: sekcja API keys (BZP, TED, email SMTP) — masked inputs | ⬜ |
| S5 | 5.16.5 | Subscription: plan free/pro badge + upgrade CTA do /pricing | ⬜ |

## FAZA 5.17 — TeamPage: użytkownicy i role
*Strona: TeamPage.tsx (145 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.17.1 | Tabela członków zespołu: GET `/api/v2/team/members` | ⬜ |
| S2 | 5.17.2 | Zaproszenie: POST `/api/v2/team/invite` — email + role (admin/user/viewer) | ⬜ |
| S3 | 5.17.3 | Zmiana roli: PATCH `/api/v2/team/members/{id}/role` | ⬜ |
| S4 | 5.17.4 | Usuń członka / dezaktywuj konto | ⬜ |
| S5 | 5.17.5 | Pending invitations: lista + resend + revoke | ⬜ |

## FAZA 5.18 — CommandMenu + FTS Search
*Komponenty: CommandMenu.tsx, TenderFTSSearch.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.18.1 | FTS search: `GET /api/v2/tenders/search?q=` — full-text z ranking | ⬜ |
| S2 | 5.18.2 | CommandMenu (Cmd+K): autocomplete tenderów z FTS | ⬜ |
| S3 | 5.18.3 | Nawigacja przez CommandMenu: goto strony, zmień filtr, otwórz tender | ⬜ |
| S4 | 5.18.4 | Historia wyszukiwań: ostatnie 10 w localStorage | ⬜ |
| S5 | 5.18.5 | Keyboard shortcuts: `?` → shortcuts modal, `G Z` → Zwiad, `G P` → Pipeline | ⬜ |

## FAZA 5.19 — MarketKPIBar + OnboardingWizard
*Komponenty: MarketKPIBar.tsx, OnboardingWizard.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.19.1 | MarketKPIBar: podłącz real dane — nowe przetargi dziś / wartość / alerty | ⬜ |
| S2 | 5.19.2 | MarketKPIBar: poll 300s — live refresh bez full-page reload | ⬜ |
| S3 | 5.19.3 | OnboardingWizard: krok 1 — uzupełnij NIP / CPV preferowane | ⬜ |
| S4 | 5.19.4 | OnboardingWizard: krok 2 — ustaw pierwszy alert email | ⬜ |
| S5 | 5.19.5 | OnboardingWizard: krok 3 — DemoTour przez Zwiad → Pipeline → Decyzja | ⬜ |

## FAZA 5.20 — ExportPage + ReportsPage
*Strony: ExportPage.tsx, ReportsPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 5.20.1 | ExportPage: eksport tenderów do CSV z filtrami (zakres dat, CPV, source) | ⬜ |
| S2 | 5.20.2 | ExportPage: eksport do XLSX — formatowane kolumny | ⬜ |
| S3 | 5.20.3 | ReportsPage: raport miesięczny — pipeline summary + win/loss | ⬜ |
| S4 | 5.20.4 | ReportsPage: generuj PDF — endpoint POST /api/v2/reports/generate | ⬜ |
| S5 | 5.20.5 | ReportsPage: scheduled reports — cron export do email (miesięcznie) | ⬜ |

---

---

# MILESTONE 6 — REALIZACJA KONTRAKTÓW (Sekcja 2)
*Cel: Moduły wykonawcze — kosztorys, oferta, logistyka, RFQ, kontrakty*

---

## FAZA 6.01 — KosztorysPage: wycena live
*Strona: KosztorysPage.tsx (1662 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.01.1 | Lista kosztorysów z `GET /api/v2/kosztorys?tender_id=X` | ⬜ |
| S2 | 6.01.2 | Nowy kosztorys: POST `/api/v2/kosztorys` — wybierz tender, nazwa | ⬜ |
| S3 | 6.01.3 | Edycja pozycji: tabela inline-edit (lp, opis, jm, ilość, cena, razem) | ⬜ |
| S4 | 6.01.4 | Sumy: netto, VAT 23%, brutto — real-time kalkulacja | ⬜ |
| S5 | 6.01.5 | Zapisz pozycje: POST/PATCH `/api/v2/kosztorys/{id}/items` | ⬜ |

## FAZA 6.02 — KosztorysPage: import ATH + AI wycena
*Strona: KosztorysPage.tsx (rozbudowa)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.02.1 | Import ATH XML: upload pliku → POST `/api/v2/kosztorys/import-ath` | ⬜ |
| S2 | 6.02.2 | AI wycena: "Wycenij automatycznie" → POST `/api/v2/kosztorys/{id}/ai-price` | ⬜ |
| S3 | 6.02.3 | ICBPriceExplorer: podłącz real dane KNR/SEKOCENBUD per pozycja | ⬜ |
| S4 | 6.02.4 | Porównaj warianty: kosztorys A vs B — diff tabela | ⬜ |
| S5 | 6.02.5 | Eksport do PDF/XLSX: formatowany kosztorys ofertowy | ⬜ |

## FAZA 6.03 — OfertaPage: kreator PDF
*Strona: OfertaPage.tsx (1584 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.03.1 | Formularz oferty: wybierz tender + kosztorys → pola formularza | ⬜ |
| S2 | 6.03.2 | Dane firmy: auto-fill z settings (NIP, adres, KRS) | ⬜ |
| S3 | 6.03.3 | Preview: renderuj ofertę HTML po prawej stronie (real-time) | ⬜ |
| S4 | 6.03.4 | Generuj PDF: POST `/api/v2/offers/generate-pdf` — pobierz plik | ⬜ |
| S5 | 6.03.5 | Biblioteka szablonów: 3 szablony (Budowlany / Usługowy / Dostawy) | ⬜ |

## FAZA 6.04 — OfertaPage: submisja i tracking
*Strona: OfertaPage.tsx (rozbudowa)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.04.1 | Historia ofert: GET `/api/v2/offers?tender_id=X` — lista złożonych | ⬜ |
| S2 | 6.04.2 | Status oferty: złożona / oczekuje / wygrana / przegrana | ⬜ |
| S3 | 6.04.3 | Wynik przetargu: wprowadź wynik (PATCH pipeline_status → WON/LOST) | ⬜ |
| S4 | 6.04.4 | Post-mortem: powód przegranej, różnica cenowa, notatki | ⬜ |
| S5 | 6.04.5 | Automatyczna sync: jeśli result_notice w BZP → update statusu | ⬜ |

## FAZA 6.05 — RfqPage: zapytania ofertowe
*Strona: RfqPage.tsx (346 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.05.1 | Lista RFQ: GET `/api/v2/rfq` — tabela z statusem | ⬜ |
| S2 | 6.05.2 | Nowe RFQ: formularz — tytuł, opis, termin, materiały | ⬜ |
| S3 | 6.05.3 | Podwykonawcy: lista firm, send email RFQ (Himalaya SMTP) | ⬜ |
| S4 | 6.05.4 | Odpowiedzi: tabela ofert od podwykonawców — import CSV / manual | ⬜ |
| S5 | 6.05.5 | Porównaj oferty: ranking automatyczny (cena + termin + rating) | ⬜ |

## FAZA 6.06 — LogistykaPage: sprzęt i pracownicy
*Strona: LogistykaPage.tsx (1362 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.06.1 | Zasoby sprzętowe: GET `/api/v2/resources?type=equipment` | ⬜ |
| S2 | 6.06.2 | Harmonogram sprzętu: calendar view — kiedy co jest zajęte | ⬜ |
| S3 | 6.06.3 | Przypisz sprzęt do przetargu/kontraktu — availability check | ⬜ |
| S4 | 6.06.4 | Koszty sprzętu: stawka/dzień → auto-kalkulacja do kosztorysu | ⬜ |
| S5 | 6.06.5 | Eksport harmonogramu sprzętu do XLSX | ⬜ |

## FAZA 6.07 — ResourcesPage: zarządzanie zespołem
*Strona: ResourcesPage.tsx (244 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.07.1 | Lista pracowników: GET `/api/v2/resources?type=human` | ⬜ |
| S2 | 6.07.2 | Profil pracownika: specjalizacje, certyfikaty, stawka | ⬜ |
| S3 | 6.07.3 | Harmonogram pracy: kto kiedy przypisany do jakiego kontraktu | ⬜ |
| S4 | 6.07.4 | Braki kadrowe: alert gdy przetarg wymaga zasobu niedostępnego | ⬜ |
| S5 | 6.07.5 | Import z CSV: masowe dodawanie pracowników/sprzętu | ⬜ |

## FAZA 6.08 — ContractsPage: tracker kontraktów
*Strona: ContractsPage.tsx (190 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.08.1 | Lista kontraktów: GET `/api/v2/contracts` — won tenders z datami | ⬜ |
| S2 | 6.08.2 | Nowy kontrakt: utwórz z przetargu WON — wartość, termin, nr umowy | ⬜ |
| S3 | 6.08.3 | Cashflow: płatności etapowe — harmonogram fakturowania | ⬜ |
| S4 | 6.08.4 | Status realizacji: PRZED / W_TRAKCIE / ZAKOŃCZONY / SPORNY | ⬜ |
| S5 | 6.08.5 | Alerty kontraktowe: deadline milestone + przeterminowane płatności | ⬜ |

## FAZA 6.09 — AutomationPage: n8n integracje
*Strona: AutomationPage.tsx (469 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.09.1 | Embedded n8n iframe (jeśli dostępny) lub lista webhooków | ⬜ |
| S2 | 6.09.2 | Pre-built automations: "Nowy przetarg → email" template cards | ⬜ |
| S3 | 6.09.3 | Webhook log: ostatnie 50 wykonań — status, payload preview | ⬜ |
| S4 | 6.09.4 | Trigger test: "Uruchom teraz" dla dowolnej automatyzacji | ⬜ |
| S5 | 6.09.5 | Custom webhook: dodaj URL → event mapping | ⬜ |

## FAZA 6.10 — ImportPage: import danych
*Strona: ImportPage.tsx (273 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.10.1 | Drag & drop upload CSV/XLSX przetargów | ⬜ |
| S2 | 6.10.2 | Column mapping: przypisz kolumny CSV → pola tender | ⬜ |
| S3 | 6.10.3 | Preview + walidacja: tabela 5 wierszy z błędami walidacji | ⬜ |
| S4 | 6.10.4 | Import: POST `/api/v2/tenders/import` — progress bar | ⬜ |
| S5 | 6.10.5 | Historia importów: lista z datą, liczbą rekordów, błędami | ⬜ |

## FAZA 6.11 — SystemPage: konfiguracja systemu
*Strona: SystemPage.tsx (340 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.11.1 | Status serwisów: health check BZP/TED/DB/Email — live | ⬜ |
| S2 | 6.11.2 | Cron jobs: lista timerów systemd + last_run + next_run | ⬜ |
| S3 | 6.11.3 | Logi ingest: ostatnie 100 linii z daily_ingest + ted_ingest | ⬜ |
| S4 | 6.11.4 | Ręczny trigger ingest: "Ingestion teraz" → POST `/api/v2/system/ingest` | ⬜ |
| S5 | 6.11.5 | DB stats: rozmiar bazy, liczba tenderów, ostatni backup | ⬜ |

## FAZA 6.12 — PogodaPage: prognoza budowlana
*Strona: PogodaPage.tsx (429 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.12.1 | Pobierz prognozę 14d: OpenMeteo API (bezpłatny) dla lokalizacji kontraktu | ⬜ |
| S2 | 6.12.2 | Wykres temp/opady/wiatr (recharts) — warunki dla robót budowlanych | ⬜ |
| S3 | 6.12.3 | Risk alert: automatyczny if T < 0°C lub opad > 20mm → ostrzeżenie | ⬜ |
| S4 | 6.12.4 | Wiele lokalizacji: dropdown dla aktywnych kontraktów | ⬜ |
| S5 | 6.12.5 | Historia pogody: jak rzeczywista pogoda wpłynęła na poprzednie kontrakty | ⬜ |

## FAZA 6.13 — AnalyticsPage: AHP + Friedman
*Strona: AnalyticsPage.tsx (554 linii, stubbed)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.13.1 | AHP kalkulacja client-side: macierz + eigenvector + CR | ⬜ |
| S2 | 6.13.2 | Test Friedmana: ranking przetargów metodą Friedmana | ⬜ |
| S3 | 6.13.3 | Win probability model: logistic regression na historical_bids | ⬜ |
| S4 | 6.13.4 | WinProbGauge: prawdopodobieństwo wygranej dla wybranego przetargu | ⬜ |
| S5 | 6.13.5 | Eksport analizy: PDF z macierzą, wykresami i rekomendacją | ⬜ |

## FAZA 6.14 — AnalyticsPage: raporty win/loss
*Strona: AnalyticsPage.tsx (rozbudowa)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.14.1 | Win/loss funnel: ile w każdym etapie pipeline co miesiąc | ⬜ |
| S2 | 6.14.2 | Analiza przegranych: powody (cena / termin / referencje / inne) | ⬜ |
| S3 | 6.14.3 | Rentowność kontraktów: margin po fakturze vs planowany | ⬜ |
| S4 | 6.14.4 | CPV performance: które CPV przynoszą najwyższy margin | ⬜ |
| S5 | 6.14.5 | YTD raport: PDF — pipeline / wyniki / przychody / prognozy | ⬜ |

## FAZA 6.15 — Toast + ErrorBoundary + Loading states
*Komponenty globalne: Toast.tsx, ErrorBoundary.tsx, SkeletonLoader.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.15.1 | Toast system: success/error/info — centralna kolejka + animacje | ⬜ |
| S2 | 6.15.2 | ErrorBoundary: wrapp wszystkie strony — friendly error screen | ⬜ |
| S3 | 6.15.3 | SkeletonLoader: ujednolicone szkielety dla kart, tabel, wykresów | ⬜ |
| S4 | 6.15.4 | Global loading bar (top progress bar przy nawigacji) | ⬜ |
| S5 | 6.15.5 | Offline detection: banner gdy brak internetu + retry on reconnect | ⬜ |

## FAZA 6.16 — Responsive + mobile
*Całość UI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.16.1 | Sidebar: hamburger menu na mobile (<768px) — slide-over | ⬜ |
| S2 | 6.16.2 | ZwiadPage mobile: tabela → cards stacked | ⬜ |
| S3 | 6.16.3 | Pipeline mobile: kanban → single column z horizontal scroll | ⬜ |
| S4 | 6.16.4 | Dashboard mobile: grid → single column | ⬜ |
| S5 | 6.16.5 | Touch targets: min 44px, swipe gestures na drawer | ⬜ |

## FAZA 6.17 — Dark mode + theming
*Całość UI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.17.1 | CSS variables: zdefiniuj full token set (colors, spacing, radius) | ⬜ |
| S2 | 6.17.2 | Dark mode toggle: localStorage persist + system preference | ⬜ |
| S3 | 6.17.3 | Wszystkie komponenty: dark: klasy Tailwind — weryfikacja kontrastu | ⬜ |
| S4 | 6.17.4 | Charts dark mode: recharts theme override | ⬜ |
| S5 | 6.17.5 | Print styles: @media print — ukryj sidebar, nav, buttons | ⬜ |

## FAZA 6.18 — Accessibility (a11y)
*Całość UI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.18.1 | ARIA roles: tablist, listbox, dialog, status — audit całości | ⬜ |
| S2 | 6.18.2 | Keyboard navigation: Tab order, focus ring visible, Escape zamyka | ⬜ |
| S3 | 6.18.3 | Screen reader: aria-label na ikonkach, sr-only text | ⬜ |
| S4 | 6.18.4 | Color contrast: WCAG AA — wszystkie texty ≥ 4.5:1 | ⬜ |
| S5 | 6.18.5 | Axe-core audit: 0 violations w CI (vitest + axe) | ⬜ |

## FAZA 6.19 — Performance
*Całość UI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.19.1 | Bundle analysis: `next build --analyze` — identyfikuj top 5 bloatów | ⬜ |
| S2 | 6.19.2 | Code splitting: lazy load stron (dynamic import) — zmniejsz initial JS | ⬜ |
| S3 | 6.19.3 | Image optimization: next/image dla logo, awatarów | ⬜ |
| S4 | 6.19.4 | API caching: SWR/react-query stale-while-revalidate na listach | ⬜ |
| S5 | 6.19.5 | Lighthouse CI: score ≥ 85 performance, 90 accessibility | ⬜ |

## FAZA 6.20 — E2E tests + CI
*Tests: Playwright*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 6.20.1 | Playwright setup: `npx playwright install`, config dla :3001 | ⬜ |
| S2 | 6.20.2 | Test: login → dashboard → zwiad (happy path) | ⬜ |
| S3 | 6.20.3 | Test: dodaj przetarg do pipeline → zmień status | ⬜ |
| S4 | 6.20.4 | Test: utwórz alert → sprawdź powiadomienie | ⬜ |
| S5 | 6.20.5 | CI: uruchom Playwright w GitHub Actions na PR | ⬜ |

---

---

# MILESTONE 7 — LAUNCH READINESS (Sekcja 3)
*Cel: Produkcja — landing, onboarding, pricing, demo, deploy*

---

## FAZA 7.01 — Landing page produkcja
*Strona: /home/ubuntu/terra-os/apps/ui/src/app/landing/page.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.01.1 | Hero section: nagłówek, sub, CTA "Zacznij za darmo" → /register | ⬜ |
| S2 | 7.01.2 | Features section: 3 bloki (Zwiad / Pipeline / Decyzja AI) z ikonami | ⬜ |
| S3 | 7.01.3 | Social proof: "2000+ przetargów w bazie", "Używają X firm" | ⬜ |
| S4 | 7.01.4 | Demo CTA: "Zobacz demo" → /demo (pre-filled demo account) | ⬜ |
| S5 | 7.01.5 | SEO: meta title/description, OG image, canonical, sitemap.xml | ⬜ |

## FAZA 7.02 — Pricing page
*Strona: /pricing/page.tsx + PricingPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.02.1 | Tabela planów: FREE / PRO / ENTERPRISE — feature comparison | ⬜ |
| S2 | 7.02.2 | Toggle: miesięcznie / rocznie (-20%) | ⬜ |
| S3 | 7.02.3 | Stripe Checkout: "Kup PRO" → redirect do Stripe | ⬜ |
| S4 | 7.02.4 | Webhook Stripe: subscription.created/updated → update plan w DB | ⬜ |
| S5 | 7.02.5 | Usage limits: FREE plan — 50 tenderów/mies., blokada z upgrade modal | ⬜ |

## FAZA 7.03 — Demo page
*Strona: /demo/page.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.03.1 | Auto-login demo: kliknij "Zobacz demo" → zaloguj demo@terra.os | ⬜ |
| S2 | 7.03.2 | Demo banner: "Tryb demo — dane resetowane codziennie o 3:00" | ⬜ |
| S3 | 7.03.3 | DemoTour: guided tour 5 kroków (Zwiad → Pipeline → Decyzja) | ⬜ |
| S4 | 7.03.4 | Demo reset button: "Przywróć dane demo" → POST /api/v2/demo/reset | ⬜ |
| S5 | 7.03.5 | Conversion CTA: po tour — "Zarejestruj się za darmo" | ⬜ |

## FAZA 7.04 — Docs page
*Strona: /docs/page.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.04.1 | Struktura docs: sidebar nav (Pierwsze kroki / Zwiad / Pipeline / API) | ⬜ |
| S2 | 7.04.2 | Quick start: 5-minutowy przewodnik od rejestracji do pierwszego alertu | ⬜ |
| S3 | 7.04.3 | API docs: Swagger embed lub link do /api/v2/docs | ⬜ |
| S4 | 7.04.4 | FAQ: top 10 pytań użytkowników | ⬜ |
| S5 | 7.04.5 | Search docs: FTS po treści dokumentacji (client-side Fuse.js) | ⬜ |

## FAZA 7.05 — Auth flow: rejestracja + login
*Komponent: LoginForm.tsx + nowy RegisterForm*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.05.1 | LoginForm: walidacja real-time (Zod) + show/hide hasło | ⬜ |
| S2 | 7.05.2 | RegisterForm: email, hasło, nazwa firmy, NIP — walidacja + submit | ⬜ |
| S3 | 7.05.3 | Forgot password: POST `/api/v2/auth/forgot-password` → email | ⬜ |
| S4 | 7.05.4 | Reset password: token w URL → POST `/api/v2/auth/reset-password` | ⬜ |
| S5 | 7.05.5 | JWT refresh: auto-refresh token przed wygaśnięciem (14min/15min) | ⬜ |

## FAZA 7.06 — Auth flow: ochrona tras
*Middleware Next.js + redirecty*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.06.1 | Middleware: sprawdź JWT na protected routes — redirect do /login | ⬜ |
| S2 | 7.06.2 | Role guard: viewer nie może edytować — disable przyciski + 403 handle | ⬜ |
| S3 | 7.06.3 | Session persistence: refresh token w httpOnly cookie | ⬜ |
| S4 | 7.06.4 | Logout: clear tokens + redirect + invalidate server-side | ⬜ |
| S5 | 7.06.5 | Idle timeout: po 30min bezczynności → ostrzeżenie + auto-logout | ⬜ |

## FAZA 7.07 — Error handling end-to-end
*Całość UI + API*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.07.1 | 404 page: custom not-found.tsx z linkiem do Dashboard | ⬜ |
| S2 | 7.07.2 | 500 page: custom error.tsx z "Zgłoś błąd" przyciskiem | ⬜ |
| S3 | 7.07.3 | API error interceptor: 401 → auto-logout, 429 → "Za dużo żądań" | ⬜ |
| S4 | 7.07.4 | Sentry integration: NEXT_PUBLIC_SENTRY_DSN → error tracking | ⬜ |
| S5 | 7.07.5 | Fallback UI: każda strona ma skeleton + empty state + error state | ⬜ |

## FAZA 7.08 — Vercel deployment
*Deploy produkcja*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.08.1 | Vercel login + link repo: `vercel link` → project terra-os-ui | ⬜ |
| S2 | 7.08.2 | Env vars: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_DEMO_ORG_ID w Vercel | ⬜ |
| S3 | 7.08.3 | Preview deploy na PR: GitHub integration + comment z URL | ⬜ |
| S4 | 7.08.4 | Production deploy: `vercel --prod` → terra.os domena | ⬜ |
| S5 | 7.08.5 | Edge middleware: rate limiting + geo-block (jeśli wymagane) | ⬜ |

## FAZA 7.09 — HTTPS + custom domain
*Infrastruktura*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.09.1 | DNS: A record terra.os → Vercel IP | ⬜ |
| S2 | 7.09.2 | TLS: Vercel auto-cert (Let's Encrypt) | ⬜ |
| S3 | 7.09.3 | API subdomain: api.terra.os → FastAPI (nginx reverse proxy) | ⬜ |
| S4 | 7.09.4 | CORS: API whitelist terra.os + preview.vercel.app | ⬜ |
| S5 | 7.09.5 | Health monitoring: UptimeRobot ping terra.os/health co 5min | ⬜ |

## FAZA 7.10 — Email flows
*Backend: Himalaya SMTP + szablony*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.10.1 | Szablon welcome email po rejestracji — HTML+text | ⬜ |
| S2 | 7.10.2 | Alert digest email: lista nowych przetargów z linkami | ⬜ |
| S3 | 7.10.3 | Forgot password email: token 1h, branded template | ⬜ |
| S4 | 7.10.4 | Team invitation email: accept link | ⬜ |
| S5 | 7.10.5 | Monthly report email: auto-send 1. dnia miesiąca | ⬜ |

## FAZA 7.11 — ChatWidget: AI asystent
*Komponent: ChatWidget.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.11.1 | Floating button: otwórz/zamknij czat (prawy dół) | ⬜ |
| S2 | 7.11.2 | Streaming: POST `/api/v2/ai/chat` → SSE stream odpowiedzi | ⬜ |
| S3 | 7.11.3 | Kontekst: wyślij aktualną stronę + selected tender ID w promptu | ⬜ |
| S4 | 7.11.4 | Sugestie: 3 quick-reply suggestions per stronie | ⬜ |
| S5 | 7.11.5 | Historia: localStorage 10 ostatnich wiadomości per sesja | ⬜ |

## FAZA 7.12 — AI endpoints backend
*FastAPI: nowe endpointy AI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.12.1 | POST `/api/v2/ai/decision-brief` — generate pros/cons dla tender | ⬜ |
| S2 | 7.12.2 | POST `/api/v2/ai/chat` — SSE stream, context-aware | ⬜ |
| S3 | 7.12.3 | POST `/api/v2/ai/price-estimate` — AI wycena na podstawie opisu CPV | ⬜ |
| S4 | 7.12.4 | POST `/api/v2/ai/risk-analysis` — analiza ryzyka z dokumentów SIWZ | ⬜ |
| S5 | 7.12.5 | Rate limiting AI: 20 req/godzinę per user (plan free) | ⬜ |

## FAZA 7.13 — Scoring faza 17+18 (backlog)
*Backend + UI (zaległe z CONTINUATION_ZWIAD.md)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.13.1 | Faza 17: deadline proximity bonus — `days_to_deadline` → score boost | ⬜ |
| S2 | 7.13.2 | Faza 18: historical win-rate per CPV-4 → boost 0–15% | ⬜ |
| S3 | 7.13.3 | Recalculate 2124 tenderów po scorer v3 — log diff | ⬜ |
| S4 | 7.13.4 | UI: SilnikPage — zakładka v3 diff (before/after heatmap) | ⬜ |
| S5 | 7.13.5 | Test: scorer v3 unit tests — min coverage 80% | ⬜ |

## FAZA 7.14 — Stripe + subscription enforcement
*Backend + UI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.14.1 | Stripe SDK: `pip install stripe`, config SECRET_KEY | ⬜ |
| S2 | 7.14.2 | Checkout session: POST `/api/v2/billing/checkout` → redirect URL | ⬜ |
| S3 | 7.14.3 | Webhook: `POST /api/v2/billing/webhook` → update subscriptions table | ⬜ |
| S4 | 7.14.4 | Plan enforcement: FREE ≤ 50 tenderów/mies — check w tenders_v2 | ⬜ |
| S5 | 7.14.5 | Billing portal: `POST /api/v2/billing/portal` → Stripe customer portal | ⬜ |

## FAZA 7.15 — Monitoring + observability
*Backend + infra*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.15.1 | Prometheus metrics: FastAPI instrumentator → `/metrics` endpoint | ⬜ |
| S2 | 7.15.2 | Grafana dashboard: req/s, latency p95, error rate, DB pool | ⬜ |
| S3 | 7.15.3 | Structured logging: JSON logs → pliki per serwis z rotacją 7d | ⬜ |
| S4 | 7.15.4 | Alert: Telegram notify gdy API error rate > 5% przez 5min | ⬜ |
| S5 | 7.15.5 | DB slow query log: pg_stat_statements → top-10 wolnych zapytań | ⬜ |

## FAZA 7.16 — Backup + disaster recovery
*Infra*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.16.1 | pg_dump cron: daily 02:00, retain 7d, do /var/backups/terraos/ | ⬜ |
| S2 | 7.16.2 | Offsite backup: rsync do S3/Backblaze B2 | ⬜ |
| S3 | 7.16.3 | Restore test: odtwórz DB z dumpa w staging — weryfikacja | ⬜ |
| S4 | 7.16.4 | Alembic baseline: sprawdź czy wszystkie migracje mają downgrade | ⬜ |
| S5 | 7.16.5 | Runbook DR: dokument odtworzenia systemu w < 1h | ⬜ |

## FAZA 7.17 — Security hardening
*Backend + infra*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.17.1 | OWASP headers: HSTS, CSP, X-Frame-Options, X-Content-Type | ⬜ |
| S2 | 7.17.2 | Secrets rotation: env vars do .env.vault lub AWS Secrets Manager | ⬜ |
| S3 | 7.17.3 | Dependabot: enable dla Python + Node — PR na vulnerabilities | ⬜ |
| S4 | 7.17.4 | Penetration test: ZAP baseline scan — 0 high severity issues | ⬜ |
| S5 | 7.17.5 | GDPR: data deletion endpoint POST `/api/v2/account/delete` — cascade | ⬜ |

## FAZA 7.18 — Performance backend
*FastAPI + PostgreSQL*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.18.1 | Query optimization: EXPLAIN ANALYZE top-5 wolnych endpointów | ⬜ |
| S2 | 7.18.2 | Indeksy: tenant_id+published_at, CPV GIN, FTS tsvector | ⬜ |
| S3 | 7.18.3 | Connection pool: pgbouncer lub asyncpg pool min=5 max=20 | ⬜ |
| S4 | 7.18.4 | Redis cache: market/summary, scoring/config — TTL 5min | ⬜ |
| S5 | 7.18.5 | Load test: locust 100 concurrent users — p95 < 200ms | ⬜ |

## FAZA 7.19 — Documentation + CHANGELOG
*Projekt*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.19.1 | README.md: quick start, architektura, env vars | ⬜ |
| S2 | 7.19.2 | CHANGELOG.md: M1–M7 w formacie Keep a Changelog | ⬜ |
| S3 | 7.19.3 | Architecture diagram: SVG/Excalidraw — serwisy + data flow | ⬜ |
| S4 | 7.19.4 | API documentation: OpenAPI schema kompletny (wszystkie 287 endpointów) | ⬜ |
| S5 | 7.19.5 | Contributing guide: konwencje kodu, PR template, CI gates | ⬜ |

## FAZA 7.20 — Launch checklist + go-live
*Finał*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.20.1 | Pre-launch checklist: 50-punktowa lista (security / UX / perf / legal) | ⬜ |
| S2 | 7.20.2 | Beta users: zapros 5 firm budowlanych — zbierz feedback | ⬜ |
| S3 | 7.20.3 | Bug bash: 2h team session — zbierz + prioritize issues | ⬜ |
| S4 | 7.20.4 | Go-live: production deploy + DNS cutover + monitoring ON | ⬜ |
| S5 | 7.20.5 | Post-launch: 24h monitoring, hotfix procedure, on-call rotacja | ⬜ |

---

## PODSUMOWANIE

| Milestone | Fazy | Sprinty | Zakres |
|-----------|------|---------|--------|
| **M5** — Zdobywanie kontraktów | 20 | 100 | Zwiad, Pipeline, Decyzja, AI, Market, CRM, Competitors, Settings, Team, Export |
| **M6** — Realizacja kontraktów | 20 | 100 | Kosztorys, Oferta, RFQ, Logistyka, Kontrakty, Automations, Analityka, Responsive, Dark mode, E2E |
| **M7** — Launch Readiness | 20 | 100 | Landing, Pricing, Demo, Auth hardening, Deploy, AI endpointy, Stripe, Monitoring, Security, Go-live |
| **TOTAL** | **60** | **300** | — |

## NASTĘPNY KROK
Zacznij od **FAZA 5.01** — ZwiadPage live data.
Komenda: `wróć z "m5"` aby implementować.
