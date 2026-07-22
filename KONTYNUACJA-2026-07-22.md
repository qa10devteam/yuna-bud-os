# YU-NA BudOS — Dokument Kontynuacji
**Data:** 2026-07-22 ~15:00  
**Wątek poprzedni:** "wróćmy do projektu yuna budos. mamy domene już yu-na.io"  
**Status:** Dev server żywy, TSC 0 errors, mock data częściowo wyczyszczone

---

## ŚRODOWISKO

| Zasób | Lokalizacja / Stan |
|-------|--------------------|
| UI dir | `/home/ubuntu/terra-os/apps/ui` |
| Backend dir | `/home/ubuntu/terra-os/services/api/services/api` |
| Dev server | `http://localhost:3001` (Next.js 16.2.10, Turbopack) |
| Backend API | `http://localhost:8765` (FastAPI, proxied via `/api/*`) |
| Auth demo | `demo@terra-os.pl` / `BudOS2026!` |
| Domena | `yu-na.io` (kupiona, DNS **niezakonfigurowany**) |
| Stack | Next.js 16 + TypeScript + Tailwind v4 + motion/react + Zustand |
| useAuthFetch | `src/lib/api-v2.ts` — zwraca callback, NIE dane. Użycie: `useEffect(() => { authFetch(...).then(r => r.json()).then(setData) }, [authFetch])` |
| silentGet helper | Wprowadzony w `page.tsx` — `fetch()` bez toast-errorów, zwraca `null` on error. Wzorzec preferowany dla tła. |

---

## CO ZOSTAŁO ZROBIONE (ten wątek)

### Faza 1-4: Mock Data → Real API ✅
Pliki naprawione w 2 batchach agentów:

| Plik | Co zrobiono |
|------|-------------|
| `src/app/app/page.tsx` | 5 endpointów real API, `silentGet` helper, `ActivityChart` przyjmuje `data: number[]` |
| `src/components/pages/BidIntelligencePage.tsx` | MOCK_BIDS + MOCK_STATS usunięte, `/api/v2/analytics/dashboard` podłączony |
| `src/app/app/zwiad/page.tsx` | Real API, debounce 300ms, paginacja Prev/Next, loading skeleton |
| `src/components/ZwiadPage.tsx` | Pełny rewrite — był ostatnim z MOCK_PRZETARGI |
| `src/components/pages/PipelinePage.tsx` | Real API, drag&drop PATCH `/api/v2/tenders/{id}`, optimistic update |

### Faza 5: Landing Mobile Responsive ✅
Plik: `src/app/landing/LandingClient.tsx` (877 linii)

| Fix | Stan |
|-----|------|
| NavBar hamburger (Menu/X lucide) | ✅ |
| Hero grid `lg:grid-cols-[1fr_1.15fr]` | ✅ |
| Hero image `hidden lg:block` | ✅ |
| StatsBar `grid-cols-2 md:grid-cols-4` | ✅ |
| FeaturesSection responsive grid | ✅ |
| PricingSection `flex flex-col md:flex-row` | ✅ |
| Footer responsive | ✅ |
| ScreenshotsSection opacity:0 bug | ✅ CSS `heroIn` fallback w globals.css |

### Faza 6: SEO ✅ (częściowe)
- `src/app/sitemap.ts` — istnieje, wskazuje na `yu-na.io`
- `src/app/robots.ts` — istnieje, `disallow: ['/app/', '/api/']`
- `src/app/layout.tsx` — `metadataBase: new URL('https://yu-na.io')` + `openGraph` ustawione

---

## CO POZOSTAŁO — PRIORYTETY

### 🔴 PRIORYTET 1: Backend Bugfix — pipeline-kpi (1-2h)

**Problem:** `GET /api/v2/dashboard/pipeline-kpi` zwraca 404 Not Found.

**Przyczyna:** Endpoint (linia 285 w `dashboard.py`) czyta z `mv_pipeline_kpi` — widoku zmaterializowanego który nie istnieje w bazie. Fallback inline powinien działać ale route nie jest zarejestrowany poprawnie (zwraca 404 a nie 500).

**Do sprawdzenia:**
```bash
# Sprawdź czy router jest zarejestrowany:
grep "dashboard" /home/ubuntu/terra-os/services/api/services/api/main.py
# Powinno być: app.include_router(dashboard.router)

# Sprawdź prefix:
grep "prefix\|APIRouter" /home/ubuntu/terra-os/services/api/services/api/routers/dashboard.py | head -3
```

**Fix:** Upewnić się że `dashboard.router` jest zarejestrowany BEZ prefix (endpoints mają ścieżki hardcoded jako `/api/v2/dashboard/...`). Sprawdzić linia ~452 main.py.

---

### 🔴 PRIORYTET 2: Backend — brakujące endpointy (2-3h)

**Problem:** Frontend zakłada endpointy które nie istnieją lub mają zły prefix:

| Endpoint | HTTP | Przyczyna |
|----------|------|-----------|
| `GET /api/v2/offers?limit=20` | 404 | Router `offers.py` ma prefix `/api/v1/offers` (v1 nie v2!) |
| `GET /api/v2/contracts` | 404 | Plik `contracts.py` nie istnieje w ogóle |
| `GET /api/v2/tenders?limit=1` | 404 | Wymaga auth — 401 bez tokenu (to OK) |

**Fix offers:**
```python
# W offers.py zmienić prefix:
router = APIRouter(prefix="/api/v2/offers", tags=["offers"])
# LUB dodać alias router v2 w main.py
```

**Fix contracts:**
```python
# Stworzyć /home/ubuntu/terra-os/services/api/services/api/routers/contracts.py
# Podstawowy GET /api/v2/contracts → lista z tabeli contracts/offers z status=signed
# Zarejestrować w main.py
```

---

### 🟡 PRIORYTET 3: Pozostałe Mock Data (2-3h)

Pliki z MOCK_ które agenci pominęli (nie były w scope):

| Plik | MOCK_ | Co zrobić |
|------|-------|-----------|
| `src/components/pages/DashboardPage.tsx:69` | `MOCK_TENDERS` jako fallback gdy API = 0 | Zamienić na loading skeleton, usunąć fallback |
| `src/components/pages/ContractsPage.tsx:72` | `MOCK_CONTRACTS` initial state | Zastąpić skeleton + fetch `/api/v2/contracts` |
| `src/components/pages/DocumentsPage.tsx:39` | `MOCK_DOCUMENTS` initial state | Zastąpić skeleton + fetch `/api/v2/documents` |
| `src/components/pages/KosztorysPage.tsx:141` | `MOCK_POZYCJE` initial state | Zastąpić skeleton, ma już `useAuthFetch` do ICB |
| `src/components/pages/BuyerCRMPage.tsx:81` | `MOCK_BUYERS` padding | Usunąć padding, pokazać tylko realne dane |
| `src/components/TenderDetail.tsx:108,114` | `MOCK_RED_FLAGS`, `MOCK_HISTORY` | Fallback — zastąpić empty state |
| `src/components/widgets/MarketBar.tsx:21` | `MOCK_RATES` initial state | OK — ma real fetch co 5min, tylko initial flash |

**Wzorzec naprawy (każdy plik):**
```tsx
// USUŃ:
const MOCK_XYZ = [...];
const [items, setItems] = useState<T[]>(MOCK_XYZ);

// ZAMIEŃ NA:
const [items, setItems] = useState<T[]>([]);
const [loading, setLoading] = useState(true);
// ... w useEffect: fetch → setItems → setLoading(false)
// ... w render: if (loading) return <SkeletonRows n={3} />
// ... if (!loading && items.length === 0) return <EmptyState />
```

---

### 🔴 PRIORYTET 4: DNS + Deploy (1h — wymaga działania Mateusza)

**Potrzeba:** wiedzieć u jakiego rejestratora jest yu-na.io (np. OVH, nazwa.pl, Cloudflare Registrar, GoDaddy...).

**Opcja A — Vercel NS (najprostsze):**
```
W panelu rejestratora:
NS 1: ns1.vercel-dns.com
NS 2: ns2.vercel-dns.com
```
Potem w Vercel dashboard dodać domenę yu-na.io do projektu terra-os.

**Opcja B — A record (jeśli nie można zmienić NS):**
```
A    @    76.76.21.21
CNAME www  cname.vercel-dns.com
```

**Backend public URL** (równolegle z DNS):
```bash
# Cloudflare Tunnel — najprostsze, zero nginx:
cloudflared tunnel create budos-api
cloudflared tunnel route dns budos-api api.yu-na.io
cloudflared tunnel run budos-api --url http://localhost:8765
# Jako systemd service żeby przeżywał restarty
```

**Po DNS:** Ustawić env var w Vercel:
```
NEXT_PUBLIC_API_URL=https://api.yu-na.io
```

**Deploy:**
```bash
cd /home/ubuntu/terra-os/apps/ui
pnpm build   # musi przejść z 0 errors
vercel --prod
```

---

### 🟡 PRIORYTET 5: Cleanup Kodu (1-2h)

**3 API clienty → 1:**
```
src/lib/api.ts       — plain fetch, no hooks
src/lib/api-client.ts — redirect do /auth/login (BUG: powinno być /login)
src/lib/api-v2.ts    — hooks, JEDYNY który powinien zostać
```
Zmergować api.ts + api-client.ts do api-v2.ts jako non-hook exports. Usunąć stare pliki. Sprawdzić importy.

**CSP fix (next.config.mjs):**
```js
// Obecne:
`script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com`
// Poprawne — unsafe-eval tylko dla dev:
const isDev = process.env.NODE_ENV === 'development'
`script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval' https://unpkg.com" : ""}`
```

**Dead code:**
- `src/app/landing/LandingClient.tsx` — `const reduce = useReducedMotion()` nigdy nieużywane (hero → CSS)
- `public/brand/` — B02-B08, B10-B16 nieużywane w żadnym komponencie

---

## ZNANE PROBLEMY TECHNICZNE

| Problem | Opis | Wpływ |
|---------|------|-------|
| `pipeline-kpi` 404 | Prawdopodobnie zły routing w main.py | Dashboard KPI pipeline = zawsze 0 |
| `offers` endpoint v1 nie v2 | prefix `/api/v1/offers` zamiast `/api/v2/` | Bid Intelligence history pusta |
| `contracts` endpoint brak | Router nie istnieje | ContractsPage zawsze pusta |
| Framer Motion przez tunnel | `initial={{ opacity: 0 }}` bez CSS fallbacku w `Reveal` component i innych | Sekcje niewidoczne przez tunel trycloudflare |
| `mv_pipeline_kpi` brak w DB | Widok zmaterializowany niestworzony | pipeline-kpi endpoint błąd |

---

## AKTUALNY STAN WERYFIKACJI

```
npx tsc --noEmit         → 0 errors ✅
curl :3001/app           → 200 ✅
curl :3001/landing       → 200 ✅
curl :8765/health        → {"status":"ok","db":"ok"} ✅
grep MOCK_ app/app/page  → 0 wyników ✅
grep MOCK_ zwiad/page    → 0 wyników ✅
grep MOCK_ PipelinePage  → 0 wyników ✅
grep MOCK_ BidIntel      → 0 wyników ✅
grep MOCK_ ZwiadPage     → 0 wyników ✅
Pozostałe MOCK_ pliki    → 7 plików z mockami ⚠️
```

---

## KOLEJNOŚĆ DZIAŁAŃ W NOWYM WĄTKU

```
1. Zapytaj Mateusza o rejestratora domeny yu-na.io
2. Fix backend pipeline-kpi (sprawdź routing main.py)
3. Fix offers prefix v1→v2
4. Wyczyść mock data w 7 plikach (parallel batch agentów)
5. DNS setup + Cloudflare Tunnel dla api.yu-na.io
6. pnpm build → vercel --prod
7. Cleanup (API clients merge, CSP, dead assets)
```

---

## SZYBKI START NOWEGO WĄTKU

```bash
# Sprawdź czy dev server żyje:
curl -s http://localhost:3001/app -o /dev/null -w '%{http_code}'
# Jeśli nie 200 — restart:
cd /home/ubuntu/terra-os/apps/ui && pnpm dev --port 3001

# Sprawdź backend:
curl -s http://localhost:8765/health

# Stan mock data:
grep -rn "MOCK_" src --include="*.tsx" --include="*.ts" | grep -v node_modules
```

---

*Wygenerowano przez Hermes Agent — 2026-07-22*
