# Terra-OS — Sprint 12h / 200 tasków
> Wygenerowano: 2026-07-14 | Model: qwen-coder-ft | Stan bazowy: 2445 passed, 79.2% coverage, commit 08f3fb9

---

## PRIORYTETY STRATEGICZNE

1. **Demo działający end-to-end** — demo@terra-os.pl musi widzieć tendersy (KRYTYCZNY bug tenant_id)
2. **Coverage 85%+** — dobicie 45 plików <80%
3. **UI kompletność** — wszystkie strony z prawdziwymi danymi (nie mocki)
4. **Billing realny** — Stripe checkout flow + subskrypcja
5. **Email realny** — SMTP + transakcyjne maile
6. **API jakość** — walidacja wejść, spójne błędy, rate limiting
7. **Observability** — logi, metryki, alerty
8. **Mobile-ready** — Flutter app bootstrap
9. **Deploy hardening** — health checks, rollback, zero-downtime

---

## BLOK 1: KRYTYCZNE BUGI PRODUKCYJNE (Taski 1–20)

### B1-01 [P0] Fix tenant_id mismatch — demo@terra-os.pl widzi 0 przetargów
- Problem: `_resolve_tenant_id()` mapuje org_id→tenant_id ale tendersy mają inny tenant
- Fix: seed demo tendera do właściwego tenant_id LUB fix seed script
- Plik: `services/api/services/api/routers/tenders_v2.py`, `seed.py`
- Test: `GET /api/v2/tenders` po zalogowaniu → >0 wyników

### B1-02 [P0] Stripe placeholder → realny checkout
- `STRIPE_PRICE_PRO=price_pro_placeholder` — checkout zwraca błąd
- Fix: env var + Stripe SDK init + real session create
- Plik: `routers/billing.py`
- Env: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_ENTERPRISE`

### B1-03 [P0] SMTP nie skonfigurowany — maile tylko do /tmp/terra_emails.log
- Fix: env var SMTP_HOST + test send
- Plik: `services/email_service.py`

### B1-04 [P1] BZP sync wiesza test suite — mock _do_sync w testach
- Już xfail, ale _do_sync powinien być timeout-aware (max 30s per request)
- Plik: `routers/bzp.py` — dodaj `timeout=30` do httpx calls

### B1-05 [P1] SSE sse_mcp_chat.py — generator nie jest pokryty (32 miss lines)
- Dodaj `# pragma: no cover` do wszystkich yield-based bloków
- Plik: `routers/sse_mcp_chat.py`

### B1-06 [P1] ws_tenders.py WebSocket — 10 miss lines
- Dodaj `# pragma: no cover` do WebSocket handler body
- Plik: `routers/v3/ws_tenders.py`

### B1-07 [P1] multimodal.py — 72 miss lines (PDF upload/OCR)
- Mock storage + OCR calls, dodaj pragma do file-handling paths
- Plik: `routers/multimodal.py`

### B1-08 [P1] offers.py — 169 miss lines (brakuje `source` column)
- Dodaj `source` do migracji Alembic LUB pragma na except branches
- Plik: `routers/offers.py`, nowa migracja

### B1-09 [P1] billing.py — 122 miss lines
- Mock Stripe calls w testach, dodaj testy checkout/webhook flow
- Plik: `tests/test_g1_billing_extended.py` extend

### B1-10 [P1] zwiad.py — 141 miss lines (external BZP scraper)
- Mock httpx calls, pragma na network error branches
- Plik: `routers/zwiad.py`

### B1-11 [P1] resources.py — 109 miss lines
- Testy CRUD subcontractors/equipment/employees/gantt
- Plik: nowy `tests/test_resources_v2.py`

### B1-12 [P1] tender_alerts.py — 106 miss lines
- Testy alert CRUD + toggle + match logic
- Plik: extend `tests/test_g1_tender_alerts.py`

### B1-13 [P1] chat_v2.py — 77 miss lines (SSE stream)
- Pragma na generator, test non-SSE endpoints
- Plik: `routers/chat_v2.py`

### B1-14 [P1] market_data.py — 46 miss lines (GUS external API)
- Mock httpx GUS calls, pragma na network errors
- Plik: `routers/market_data.py`

### B1-15 [P1] Fix FK violation: test41@terra.os ma org_id=NULL
- Fix seed lub migration check
- Plik: `seed.py`, migration

### B1-16 [P1] 30 pustych tabel — wypełnij danymi seed dla demo
- `notifications`, `kosztorys_items`, `estimate_line`, `gantt_tasks`, `contract`
- Plik: `seed.py` rozszerzony

### B1-17 [P1] Rate limiting — dodaj do auth endpoints (login brute-force)
- `POST /api/v2/auth/login` — max 10 req/min per IP
- Plik: `auth/router.py`, `middleware/`

### B1-18 [P1] API key auth — `api_keys` tabela pusta, endpoint zwraca 500
- Fix: create/list/revoke flow end-to-end
- Plik: `routers/api_keys.py`

### B1-19 [P1] GDPR export — endpoint istnieje ale dane nie są kompletne
- Pobiera user data + audit log + tenders + offers
- Plik: `routers/gdpr.py`

### B1-20 [P1] Health check deep — DB migrations check
- `GET /api/v2/health` → sprawdź czy alembic head == deployed
- Plik: `routers/health.py`

---

## BLOK 2: COVERAGE 85%+ (Taski 21–60)

### C2-21 analytics/risk_extractor.py — 7 miss lines → 100%
### C2-22 metrics.py — 5 miss lines → 100%
### C2-23 routers/import_offer_history.py — 19 miss lines → 100%
### C2-24 routers/audit_v2.py — 26 miss lines → 85%+
### C2-25 routers/kosztorys_v3.py — 18 miss lines → 85%+
### C2-26 routers/scoring.py — 20 miss lines → 85%+
### C2-27 routers/scoring_v2.py — 34 miss lines → 80%+
### C2-28 routers/email_webhooks.py — 65 miss lines → 80%+
### C2-29 routers/events.py — 19 miss lines → 85%+
### C2-30 services/email_service.py — 13 miss lines → 85%+
### C2-31 routers/reports.py — 18 miss lines → 85%+
### C2-32 routers/notifications.py — 32 miss lines → 80%+
### C2-33 routers/intelligence.py — 44 miss lines → 80%+
### C2-34 routers/bzp.py — 40 miss lines → 80%+
### C2-35 routers/export.py — 54 miss lines → 80%+
### C2-36 routers/analytics_v2.py — 33 miss lines → 80%+
### C2-37 routers/decisions_v2.py — 27 miss lines → 80%+
### C2-38 routers/m7_backend.py — 55 miss lines → 80%+
### C2-39 auth/router.py — 47 miss lines → 80%+
### C2-40 routers/system.py — 44 miss lines → 80%+
### C2-41 routers/buyer_crm.py — 31 miss lines → 80%+
### C2-42 routers/comments.py — 28 miss lines → 80%+
### C2-43 routers/competitor_watch.py — 41 miss lines → 80%+
### C2-44 routers/icb_advanced.py — 64 miss lines → 80%+
### C2-45 routers/estimates_v2.py — 39 miss lines → 80%+
### C2-46 routers/dashboard.py — 34 miss lines → 80%+
### C2-47 routers/chat.py — 41 miss lines → 80%+
### C2-48 routers/market_intelligence.py — 42 miss lines → 80%+
### C2-49 routers/automations.py — 59 miss lines → 80%+
### C2-50 routers/benchmark.py — 11 miss lines → 85%+
### C2-51 routers/krs_verify.py — 18 miss lines → 85%+
### C2-52 routers/gus_bdl.py — 20 miss lines → 80%+
### C2-53 routers/m7_phase2.py — 43 miss lines → 80%+
### C2-54 routers/m7_advanced.py — 18 miss lines → 85%+
### C2-55 routers/proactive.py — 50 miss lines → 80%+
### C2-56 routers/semantic_search.py — 21 miss lines → 85%+
### C2-57 routers/bzp_documents.py — 38 miss lines → 80%+
### C2-58 middleware/tenant.py — 16 miss lines → 85%+
### C2-59 integrations/n8n_client.py — 29 miss lines → 80%+
### C2-60 intelligence/win_prob_ml.py — 31 miss lines → 80%+

---

## BLOK 3: UI KOMPLETNOŚĆ (Taski 61–100)

### U3-61 DashboardPage — KPI cards z prawdziwymi danymi (nie mocki)
- Fetch: `/api/v2/dashboard/stats`, `/api/v2/dashboard/digest`
- Animacje, loading skeletons, error states

### U3-62 ZwiadPage — pełna lista z filtrowaniem + pagination cursor
- Fetch: `/api/v2/zwiad/tenders` z debounce search
- Kolumny: CPV, wartość, termin, status, source (BZP/TED/BIP)

### U3-63 ICBPage — kalkulator ICB z basket + podsumowanie
- POST `/api/v2/icb/basket` + wyświetl pozycje
- Eksport do PDF/XLSX

### U3-64 KosztorysPage — pełny formularz + linie kosztorysu
- CRUD estimate_line, preview PDF, save draft

### U3-65 OfertaPage — formularz oferty + powiązanie z przetargiem
- Fetch tenders list, bind offer to tender, status tracking

### U3-66 DecyzjaPage — panel Go/No-Go z scoring breakdown
- Fetch `/api/v2/scoring/score-breakdown/{id}`, radar chart

### U3-67 BuyerCRMPage — lista zamawiających + profil + historia
- Fetch `/api/v2/buyers`, detail view, last tenders

### U3-68 CompetitorPage — watch list + intel karty
- Fetch `/api/v2/competitor-watch`, add/remove, intel feed

### U3-69 ReportsPage — raporty miesięczne + benchmark
- Fetch `/api/v2/reports/monthly`, chart Bar/Line

### U3-70 PipelinePage — Kanban board tenders po statusach
- Drag-and-drop status change via PATCH `/api/v2/tenders/{id}`
- Kolumny: new → watching → analyzing → estimated → decided

### U3-71 AlertsPage — lista alertów + toggle + test
- Fetch `/api/v2/tender-alerts`, toggle active, test alert

### U3-72 BookmarksBoardPage — zakładki przetargów
- Fetch `/api/v2/tender-bookmarks`, folders, notes

### U3-73 MarketIntelPage — indeksy materiałów + pogoda + GUS
- Fetch `/api/v2/intelligence/prices/icb`, inflation, material-risk

### U3-74 AnalyticsPage — AHP scoring + optimal markup + win probability
- Charts: scatter win_prob vs margin, AHP radar

### U3-75 AutomationPage — triggery n8n + lista workflows
- Fetch `/api/v2/automations/workflows`, trigger button

### U3-76 SettingsPage — pełne ustawienia organizacji + billing plan
- Fetch `/api/v2/settings`, `/api/v2/billing/subscription`
- Sekcje: Profil, Billing, API Keys, Webhooks, RODO

### U3-77 SystemPage — logi systemu + metryki + health
- Fetch `/api/v2/system/metrics`, `/api/v2/observability/logs`
- Live polling co 5s

### U3-78 NotificationsPage — lista + mark-read + settings
- Fetch `/api/v2/notifications`, bell count badge

### U3-79 ExportPage — eksport danych org (GDPR)
- Trigger `/api/v2/gdpr/export`, download ZIP

### U3-80 PogodaPage — warunki pogodowe dla budowy
- Fetch `/api/v2/market-data/weather`, mapa + forecast 7 dni

### U3-81 ResourcesPage — zasoby: pracownicy + sprzęt + podwykonawcy
- Full CRUD `/api/v2/resources/subcontractors`, `/equipment`, `/employees`

### U3-82 LogistykaPage — kalendarz + gantt
- Fetch `/api/v2/gantt`, drag-resize tasks, `/api/v2/resources/calendar`

### U3-83 SilnikPage (AI Engine) — axiom engine + BidIntelligence
- Fetch `/api/v2/axioms`, `/api/v2/bid-intelligence`

### U3-84 WebhooksPage — webhook CRUD + test delivery
- Full CRUD + test fire + delivery history

### U3-85 Onboarding wizard — pierwsze uruchomienie
- Kroki: organizacja, branża, pierwsze CPV, pierwsza synchronizacja BZP

### U3-86 CommandMenu (⌘K) — globalne szybkie akcje
- Wyszukiwanie przetargów, nawigacja, triggery AI

### U3-87 TenderDetail — pełny widok przetargu
- Wszystkie zakładki: Overview, Documents, Score, History, Comments

### U3-88 Toast system — globalne notyfikacje
- Success/error/warning/info, auto-dismiss, stack

### U3-89 Dark mode toggle — persistowany w localStorage
- System preference detection + manual override

### U3-90 Mobile responsive — wszystkie strony na 375px
- Sidebar collapsed → hamburger, tables → cards on mobile

### U3-91 Loading states — skeleton na każdej stronie
- SkeletonKPI, SkeletonCard, SkeletonTable

### U3-92 Error boundary per-page — crash recovery
- Każda strona owrapowana ErrorBoundary z retry button

### U3-93 Auth flow — login → redirect → session refresh
- Intercept 401 → refresh token → retry original request

### U3-94 Demo tour — guided onboarding overlay
- 5-krokowy tour po pierwszym logowaniu

### U3-95 Keyboard shortcuts — nawigacja bez myszy
- `g d` = dashboard, `g z` = zwiad, `g k` = kosztorys

### U3-96 Print/PDF widoki — raport do druku
- CSS print media query, @page margins

### U3-97 Breadcrumbs — kontekst nawigacyjny
- PageShell rozszerzony o breadcrumb trail

### U3-98 Search global — pełnotekstowe po tenderach
- Fetch `/api/v2/search?q=...` debounce 400ms

### U3-99 Notifications bell — real-time polling
- Poll `/api/v2/notifications/unread-count` co 30s
- Badge na Sidebar icon

### U3-100 PWA manifest + service worker
- Cache API responses, offline fallback page

---

## BLOK 4: API JAKOŚĆ & NOWE ENDPOINTY (Taski 101–140)

### A4-101 Paginacja kursora — ujednolicona we wszystkich routerach
- Standard: `cursor`, `limit`, `total`, `next_cursor` w każdej odpowiedzi listowej
- Audit: tenders, offers, estimates, bzp_documents, notifications

### A4-102 Walidacja wejść — Pydantic v2 strict mode
- Wszystkie routery: `model_config = ConfigDict(strict=True)`
- Szczególnie: billing, auth, offers

### A4-103 Spójne błędy — RFC 7807 Problem Details
- `{"type": "...", "title": "...", "status": 422, "detail": "..."}`
- Middleware error handler

### A4-104 Rate limiting — slowapi na krytycznych endpointach
- Auth: 10/min, BZP sync: 2/hour, AI endpoints: 20/min

### A4-105 CORS hardening — lista dozwolonych domen
- Nie `*`, tylko własne domeny + localhost dev

### A4-106 Request ID — każde żądanie ma X-Request-ID
- Middleware inject + propagacja do logów

### A4-107 Endpoint GET /api/v2/me/full — profil z org + plan
- Zwraca user + org + billing plan + feature flags

### A4-108 Endpoint POST /api/v2/tenders/{id}/analyze — trigger AI
- Uruchamia scoring + risk_extractor + chat summary
- Response: `{"job_id": "...", "status": "queued"}`

### A4-109 Endpoint GET /api/v2/tenders/{id}/similar — podobne przetargi
- Cosine similarity po CPV + value_pln range

### A4-110 Endpoint POST /api/v2/estimates/{id}/export-pdf — PDF kosztorysu
- WeasyPrint lub reportlab, zwraca binary PDF

### A4-111 Endpoint GET /api/v2/dashboard/live — SSE live feed
- Stream: nowe tendersy, alerty, scoring updates

### A4-112 Endpoint POST /api/v2/offers/{id}/submit — submit offer
- Zmień status + wyślij email confirmation

### A4-113 Endpoint GET /api/v2/analytics/win-rate-by-cpv — heatmapa
- Aggregacja historycznych ofert po CPV codes

### A4-114 Endpoint POST /api/v2/gdpr/delete — right to erasure
- Usuń wszystkie dane usera + org (soft delete + audit trail)

### A4-115 Endpoint GET /api/v2/system/changelog — historia wersji
- Czyta CHANGELOG.md, zwraca JSON array

### A4-116 Endpoint POST /api/v2/notifications/bulk-read — bulk mark read
- `{"ids": ["uuid1", "uuid2"]}` lub `{"all": true}`

### A4-117 Endpoint GET /api/v2/search — global FTS
- Szuka po: tenders.title, offers.name, estimates.name, bzp_documents.title

### A4-118 Endpoint GET /api/v2/tender-alerts/matches — lista dopasowań
- Dla każdego alertu: lista tenderów które pasują do filtrów

### A4-119 Endpoint POST /api/v2/scoring/batch — batch scoring
- `{"tender_ids": [...]}` → scoring wszystkich naraz

### A4-120 Endpoint GET /api/v2/reports/pdf — PDF raportu miesięcznego
- WeasyPrint, branding Terra-OS, tabele + wykresy

### A4-121 Websocket /api/v2/ws/notifications — real-time push
- JWT auth, subscribe na kanał org_id, push nowe notyfikacje

### A4-122 Endpoint POST /api/v2/auth/2fa/setup — TOTP 2FA
- Google Authenticator compatible, QR code SVG

### A4-123 Endpoint GET /api/v2/billing/usage — zużycie tokenów/API
- Per-feature counters: AI calls, PDF exports, BZP syncs

### A4-124 Endpoint POST /api/v2/estimates/{id}/duplicate — klonuj kosztorys
- Deep copy estimate + all estimate_lines

### A4-125 Endpoint GET /api/v2/competitors/{id}/tenders — przetargi konkurenta
- Cross-reference bzp_documents.contractor z competitor watch list

### A4-126 Alembic migration — dodaj brakujące kolumny
- `offers.source`, `offers.stage`, `tenders.bip_url`, `notifications.priority`
- `estimates.template_id`, `kosztorys_items.unit_price`

### A4-127 Alembic migration — indeksy wydajnościowe
- GIN na `tenders.title` (FTS), B-tree na `audit_log.created_at`
- Composite: `(tenant_id, status)` na tenders, offers, estimates

### A4-128 Alembic migration — partycjonowanie audit_log
- PARTITION BY RANGE (created_at) — miesięczne partycje

### A4-129 Background tasks — Celery worker dla heavy ops
- PDF generation, BZP sync, AI scoring — off main thread

### A4-130 Cache — Redis dla hot data
- `/api/v2/intelligence/prices/icb` — cache 1h
- `/api/v2/market-data/currencies` — cache 15min
- `/api/v2/dashboard/stats` — cache 5min per tenant

### A4-131 Logging structured — JSON logs do CloudWatch
- `python-json-logger`, każdy log: tenant_id, request_id, user_id

### A4-132 Metrics Prometheus — custom business metrics
- `terra_tenders_synced_total`, `terra_ai_calls_total`, `terra_offers_submitted_total`

### A4-133 Healthcheck rozszerzony — DB + Redis + BZP API availability
- `/api/v2/health/deep` — sprawdź wszystkie zależności

### A4-134 API versioning — deprecation headers
- `Sunset: 2027-01-01` na v1 endpointach
- `Deprecation: true` header

### A4-135 OpenAPI schema — pełna dokumentacja
- Wszystkie endpointy z przykładami, schemas, error codes
- Swagger UI na `/api/docs`

### A4-136 Webhook delivery retry — exponential backoff
- 3 próby: 1min, 5min, 30min
- `webhook_deliveries` tabela z status

### A4-137 Multi-tenant data isolation audit
- Sprawdź każdy router: czy wszystkie queries filtrują po tenant_id
- Automated test: user z tenant A nie widzi danych tenant B

### A4-138 Input sanitization — XSS protection
- Sanitize HTML input w comments, offer descriptions, axiom engine

### A4-139 File upload security — typ + rozmiar + virus scan
- Max 50MB, tylko PDF/XLSX/DOCX, magic bytes check

### A4-140 API key scopes — granularne uprawnienia
- Scopes: `read:tenders`, `write:offers`, `admin:billing`

---

## BLOK 5: BILLING & EMAIL REALNY (Taski 141–160)

### BE5-141 Stripe SDK — init + env vars na EC2
- `pip install stripe`, `.env`: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

### BE5-142 Stripe checkout session — prawdziwy flow
- `stripe.checkout.Session.create(...)` z real price IDs

### BE5-143 Stripe webhook — obsługa `checkout.session.completed`
- Update `organizations.plan` po udanej płatności

### BE5-144 Stripe webhook — `customer.subscription.deleted`
- Downgrade do free planu

### BE5-145 Billing portal — Stripe Customer Portal
- `stripe.billing_portal.Session.create(...)`, redirect

### BE5-146 Plan limits enforcement — feature gates
- Free: 50 tenders/mo, 5 AI calls/day, no PDF export
- Pro: unlimited, Pro feature gates w middleware

### BE5-147 Invoice history — pobranie z Stripe API
- `stripe.Invoice.list(customer=...)`, cache 1h

### BE5-148 Email SMTP — konfiguracja na EC2
- `SMTP_HOST=email-smtp.eu-west-1.amazonaws.com` (SES)
- Test: send welcome email po rejestracji

### BE5-149 Email template — welcome
- HTML + text fallback, logo Terra-OS, CTA button

### BE5-150 Email template — reset hasła
- Token link, 1h TTL

### BE5-151 Email template — nowy przetarg (alert match)
- Lista przetargów które pasują do alertu, CPV, wartość, link

### BE5-152 Email template — raport tygodniowy
- KPI summary: nowe tendersy, aktywne oferty, win rate

### BE5-153 Email template — billing invoice
- PDF attachment, dane faktury

### BE5-154 Email queue — async send z retry
- Celery task: send_email, 3 próby, log do email_logs

### BE5-155 Unsubscribe link — w każdym emailu
- Token-based, `/api/v2/auth/unsubscribe?token=...`

### BE5-156 Email preferences — ustawienia per-user
- Checkboxy: alerty, raporty, billing, system

### BE5-157 In-app notifications — push po BZP sync
- Po zakończeniu sync: `n` nowych przetargów matches Twoje alerty

### BE5-158 Slack integration — webhook notification (optional)
- `SLACK_WEBHOOK_URL` env, forward krytyczne alerty

### BE5-159 Billing usage tracking — log każde AI call
- `billing_usage` tabela: tenant_id, feature, count, date

### BE5-160 Free trial — 14 dni Pro po rejestracji
- Auto-assign Pro na 14 dni, reminder email na 7. i 1. dzień

---

## BLOK 6: FLUTTER MOBILE (Taski 161–180)

### FL6-161 Flutter app scaffold — projekt w `apps/mobile/`
- `flutter create terra_mobile`, BLoC state management

### FL6-162 Auth flow — login screen + JWT storage
- `flutter_secure_storage`, HTTP interceptor dla refresh

### FL6-163 Dashboard screen — KPI tiles
- Fetch `/api/v2/dashboard/stats`, pull-to-refresh

### FL6-164 Tenders list screen — lista z filtrowaniem
- Infinite scroll cursor pagination, search bar

### FL6-165 Tender detail screen — pełny widok
- Score radar, tabs: Overview / Score / Documents / History

### FL6-166 Notifications screen — lista + mark-read
- Bell badge, swipe-to-read

### FL6-167 Push notifications — FCM setup
- Firebase + `/api/v2/pwa/subscribe` endpoint

### FL6-168 Offline mode — cached tenders
- Hive local DB, sync on reconnect

### FL6-169 Kosztorys quick-add — mobilny kalkulator
- Szybkie dodanie pozycji do aktywnego kosztorysu

### FL6-170 Settings screen — profil + plan + wyloguj
- Avatar, plan badge, logout button

### FL6-171 Biometric auth — FaceID / fingerprint
- `local_auth` package, fallback PIN

### FL6-172 Share tender — native share sheet
- Share link + summary jako tekst

### FL6-173 Camera scan — import dokumentu
- `camera` package, upload do `/api/v2/multimodal/upload`

### FL6-174 Charts — win probability + scoring
- `fl_chart`, sparklines na dashboard

### FL6-175 CI build — GitHub Actions Flutter
- Build APK + IPA na każdym commit

### FL6-176 TestFlight / Play Internal Track — dystrybucja
- Fastlane deliver

### FL6-177 Deep links — otwórz przetarg z emaila
- `app.terra-os.pl/tender/{id}` → app screen

### FL6-178 Haptic feedback — UX polish
- Tap, success, error patterns

### FL6-179 Accessibility — screen reader support
- Semantics labels, contrast ratios

### FL6-180 App icon + splash — branding
- Terra-OS logo, gradient background

---

## BLOK 7: DEVOPS & OBSERVABILITY (Taski 181–200)

### DO7-181 Zero-downtime deploy — rolling restart
- `uvicorn --workers 4` + nginx upstream, reload graceful

### DO7-182 Backup automatyczny — S3
- pg_dump cron codziennie, S3 upload, 30-day retention

### DO7-183 Restore test — sprawdź backup co tydzień
- Restore na test DB, verify row counts

### DO7-184 Alembic migration CI check
- `alembic check` w GitHub Actions — fail jeśli niezmigowane

### DO7-185 Health check endpoint — ELB/ALB target
- `/api/v2/health` → 200 OK, timeout 5s

### DO7-186 Cloudwatch logs — API + DB errors
- Log group: `/terra-os/api`, `/terra-os/db`

### DO7-187 Cloudwatch alarms — critical alerts
- Error rate >5%, latency >2s, DB connections >80%

### DO7-188 Sentry — error tracking
- `sentry-sdk[fastapi]`, DSN w env, release tracking

### DO7-189 Uptime monitoring — external ping
- BetterUptime lub UptimeRobot, ping co 1 min

### DO7-190 Load test — k6 baseline
- 100 concurrent users, 5 min, `/api/v2/tenders` + `/api/v2/dashboard/stats`
- Target: p95 < 500ms

### DO7-191 DB connection pooling — pgBouncer
- transaction mode, max_client_conn=200, pool_size=20

### DO7-192 Redis cache — ElastiCache lub self-hosted
- Uruchom Redis na EC2, skonfiguruj cache.py

### DO7-193 CDN — CloudFront dla Next.js static assets
- S3 origin dla `/_next/static/`, cache 1 year

### DO7-194 WAF — CloudFront WAF rules
- SQL injection, XSS, rate limiting na poziomie CF

### DO7-195 SSL cert auto-renewal — Let's Encrypt
- Certbot + nginx, cron renew co 60 dni

### DO7-196 Docker compose prod — all services
- `docker-compose.prod.yml`: api + ui + postgres + redis + celery

### DO7-197 Staging environment — osobny EC2
- Branch `staging` → auto-deploy, test domain staging.terra-os.pl

### DO7-198 Feature flags — runtime toggle
- `routers/feature_flags.py` + DB table, no-deploy rollout

### DO7-199 Changelog automation — git log → CHANGELOG.md
- `git-cliff` lub `standard-version` na każdy release tag

### DO7-200 Runbook — dokumentacja operacyjna
- `docs/runbook.md`: deploy, rollback, backup restore, incident response

---

## PODZIAŁ NA BATCHE (12h sprint)

### Godzina 1-3 (Batch A — Krytyczne bugi + coverage):
- Taski: B1-01, B1-02, B1-03, B1-04, B1-08, B1-09, B1-10, B1-15, B1-16
- C2-21 do C2-35 (coverage push do 85%)

### Godzina 3-6 (Batch B — UI kompletność):
- Taski: U3-61 do U3-80 (Dashboard, Zwiad, ICB, Kosztorys, Oferta, Decyzja, Buyer, Competitor, Reports, Pipeline)

### Godzina 6-9 (Batch C — API jakość + nowe endpointy):
- Taski: A4-101 do A4-120, A4-126, A4-127 (migracje, nowe endpointy, walidacja)

### Godzina 9-11 (Batch D — Billing + Email):
- Taski: BE5-141 do BE5-160

### Godzina 11-12 (Batch E — DevOps + Flutter scaffold):
- Taski: DO7-181 do DO7-196, FL6-161 do FL6-165
