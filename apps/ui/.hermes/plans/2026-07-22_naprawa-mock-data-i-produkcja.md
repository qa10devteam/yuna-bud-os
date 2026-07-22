# YU-NA BudOS — Plan Naprawy: Mock Data → Real API + Launch

> **Dla agenta:** Implementować task po tasku, branch per faza, PR po każdej fazie.

**Cel:** Wyeliminować mock data, odpalić na yu-na.io, mobile ready.  
**Stack:** Next.js 16 / FastAPI (port 8765) / PostgreSQL / Zustand / Tailwind v4  
**UI dir:** `/home/ubuntu/terra-os/apps/ui`  
**API dir:** `/home/ubuntu/terra-os/services/api/services/api`  
**Konta dev:** `demo@terra-os.pl` / BudOS2026!

---

## FAZA 1 — Dashboard & KPI: real data (est. 3-4h)

Endpointy backendu już istnieją:
- `GET /api/v2/dashboard/stats` → liczby KPI
- `GET /api/v2/dashboard` → główny digest
- `GET /api/v2/dashboard/pipeline-kpi` → funnel pipeline
- `GET /api/v2/analytics/win-rate-trend` → wykres win rate

### Task 1.1: Podłącz KPI cards na Dashboard

**Plik:** `src/app/app/page.tsx`  
**Zmiana:** zamień hardcoded `MOCK_STATS` → `useAuthFetch('/api/v2/dashboard/stats')`

```tsx
// Obecny kod:
const MOCK_STATS = { oferty: 24, wartosc: "2.4M PLN", winRate: "34%" }

// Nowy kod:
const { data: stats, isLoading } = useAuthFetch<DashboardStats>('/api/v2/dashboard/stats')
```

**Weryfikacja:** Dashboard powinien pokazywać realne dane z bazy. Jeśli API zwraca 0 — to poprawne (pusta baza).

### Task 1.2: Podłącz Activity Chart

**Plik:** `src/app/app/page.tsx`  
**Zmiana:** `CHART_DATA` → `useAuthFetch('/api/v2/analytics/win-rate-trend')`

**Typ odpowiedzi:**
```ts
interface WinRateTrend {
  month: string;
  win_rate: number;
  total: number;
}[]
```

### Task 1.3: Podłącz Recent Tenders list

**Plik:** `src/app/app/page.tsx`  
**Zmiana:** `MOCK_PRZETARGI` (lista ostatnich) → `useAuthFetch('/api/v2/tenders?limit=5&sort=created_at:desc')`

### Task 1.4: Loading skeleton dla Dashboard

Gdy `isLoading === true` → wyświetl skeleton (animate-pulse divs) zamiast pustego miejsca.

---

## FAZA 2 — Zwiad/Przetargi: real data (est. 4-6h)

Endpointy:
- `GET /api/v2/tenders?q=&cpv=&province=&value_min=&limit=20&offset=0` → lista przetargów
- `GET /api/v2/tenders/{id}` → szczegóły
- `GET /api/v2/tenders/{id}/analyze` → AI analiza

### Task 2.1: Zamień MOCK_TENDERS w ZwiadPage na API

**Pliki:** `src/app/app/zwiad/page.tsx`, `src/components/ZwiadPage.tsx`  
**Zmiana:**
```tsx
// Usuń:
const MOCK_TENDERS = [...]

// Dodaj:
const [page, setPage] = useState(0)
const { data, isLoading } = useAuthFetch<TendersResponse>(
  `/api/v2/tenders?limit=20&offset=${page * 20}${filters}`
)
```

### Task 2.2: Podłącz filtry do API

Filtry (CPV, województwo, wartość, źródło) muszą trafiać jako query params do `/api/v2/tenders`.  
Obecny stan: filtrowanie lokalne po tablicy mock. Nowy stan: każda zmiana filtra = nowy fetch.

### Task 2.3: Paginacja przetargów

Dodać `offset`/`limit` z backendu. Backend zwraca `{ items: [], total: number }`.  
Dodać komponent `Pagination` pod listą.

### Task 2.4: Zamień MOCK_PRZETARGI w ZwiadPage.tsx

Ten sam plik ma drugą kopię mock data. Ujednolicić — jeden hook, jeden fetch.

---

## FAZA 3 — Pipeline: real data (est. 2-3h)

Endpoint: `GET /api/v2/tenders?pipeline_status=scouting|qualified|offer|won|lost`

### Task 3.1: Kanban kolumny z API

**Plik:** `src/components/PipelinePage.tsx`  
**Zmiana:** Usuń `MOCK_` fallback. Fetch każdej kolumny osobno lub jeden fetch + grupowanie:
```tsx
const { data } = useAuthFetch<TendersResponse>('/api/v2/tenders?include_pipeline=true&limit=100')
const columns = groupBy(data?.items, 'pipeline_status')
```

### Task 3.2: Drag & drop → PATCH pipeline_status

Gdy karta zostaje przeniesiona między kolumnami:
```tsx
await authFetch(`/api/v2/tenders/${id}`, {
  method: 'PATCH',
  body: JSON.stringify({ pipeline_status: newColumn })
})
```

---

## FAZA 4 — Bid Intelligence: odkomenuj API (est. 1-2h)

Plik: `src/app/app/bid-intelligence/BidIntelligencePage.tsx`  
Jest TODO na linii 63: `// TODO: restore API call when backend is available`

Endpointy dostępne:
- `GET /api/v2/analytics/dashboard` → statystyki ofert
- `GET /api/v2/analytics/win-rate-trend` → trend win rate

### Task 4.1: Odkomenuj API call w BidIntelligencePage

```tsx
// Usuń:
// TODO: restore API call when backend is available
const MOCK_STATS = { ... }
const MOCK_BIDS = [...]

// Dodaj:
const { data: stats } = useAuthFetch<BidStats>('/api/v2/analytics/dashboard')
const { data: history } = useAuthFetch<BidHistory[]>('/api/v2/analytics/win-rate-trend')
```

### Task 4.2: Ujednolicić typy z odpowiedzią API

Sprawdzić `GET /api/v2/analytics/dashboard` response shape i dostosować komponenty.

---

## FAZA 5 — Mobile Responsywność Landing (est. 4-6h)

**Plik:** `src/app/landing/LandingClient.tsx` (886 linii)  
**Problem:** 100% inline styles, zero breakpointów, overflow na małych ekranach.

### Task 5.1: NavBar mobile

```tsx
// Dodaj hamburger menu dla md:hidden
// Desktop: flex row | Mobile: hamburger → overlay menu
```

**Komponenty do zmiany:**
- `NavBar` — dodaj `useState(menuOpen)` + hamburger button
- `<nav className="hidden md:flex ...">` 
- `<button className="md:hidden ..." onClick={toggleMenu}>`

### Task 5.2: Hero grid responsive

```tsx
// Obecne: style={{ display: 'grid', gridTemplateColumns: '1fr 1.15fr' }}
// Nowe (Tailwind):
<div className="grid grid-cols-1 lg:grid-cols-[1fr_1.15fr] gap-12 lg:gap-16">
```

### Task 5.3: Stats bar responsive

```tsx
// grid-cols-2 md:grid-cols-4
```

### Task 5.4: Features grid responsive

```tsx
// grid-cols-1 md:grid-cols-2 lg:grid-cols-3
```

### Task 5.5: Pricing cards responsive

```tsx
// flex-col md:flex-row na karty, usuń minWidth: 240 inline style
```

### Task 5.6: Typography scaling

```tsx
// H1: text-4xl md:text-5xl lg:text-6xl
// H2: text-3xl md:text-4xl
// Body: text-base md:text-lg
```

### Task 5.7: Screenshots section na mobile

Tab switcher → scroll horizontal na mobile (overflow-x-auto snap-x).

---

## FAZA 6 — SEO & PWA (est. 2h)

### Task 6.1: metadataBase + OG image

**Plik:** `src/app/layout.tsx`
```tsx
export const metadata: Metadata = {
  metadataBase: new URL('https://yu-na.io'),
  openGraph: {
    images: [{ url: '/brand/B04-og-dark.png', width: 1200, height: 630 }]
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/brand/B04-og-dark.png']
  }
}
```

### Task 6.2: sitemap.ts

**Plik:** `src/app/sitemap.ts`
```ts
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: 'https://yu-na.io/landing', changeFrequency: 'weekly', priority: 1 },
    { url: 'https://yu-na.io/login', changeFrequency: 'monthly', priority: 0.5 },
  ]
}
```

### Task 6.3: robots.ts

**Plik:** `src/app/robots.ts`
```ts
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/', disallow: '/app/' },
    sitemap: 'https://yu-na.io/sitemap.xml'
  }
}
```

### Task 6.4: PWA ikony

```bash
# Wygeneruj z SVG:
convert public/icons/icon.svg -resize 192x192 public/icons/icon-192.png
convert public/icons/icon.svg -resize 512x512 public/icons/icon-512.png
```

---

## FAZA 7 — DNS & Deploy (est. 1h konfiguracja)

### Task 7.1: DNS yu-na.io → Vercel

1. Zaloguj do rejestratora domeny yu-na.io
2. Zmień NS na: `ns1.vercel-dns.com`, `ns2.vercel-dns.com`
3. LUB dodaj: `A @ 76.76.21.21` (Vercel IP)

### Task 7.2: Vercel projekt + env

```bash
cd /home/ubuntu/terra-os
vercel link   # lub przez dashboard
# Dodaj env var:
# NEXT_PUBLIC_API_URL = https://api.yu-na.io (lub EC2 public IP)
```

### Task 7.3: Backend public URL

Opcje (wybierz jedną):
- **A) Cloudflare Tunnel (najprostsze):**
  ```bash
  cloudflared tunnel create budos-api
  cloudflared tunnel route dns budos-api api.yu-na.io
  cloudflared tunnel run budos-api
  ```
- **B) nginx + Let's Encrypt na EC2:**
  ```nginx
  server {
    server_name api.yu-na.io;
    location / { proxy_pass http://localhost:8765; }
  }
  ```

### Task 7.4: Build & deploy

```bash
cd /home/ubuntu/terra-os/apps/ui
pnpm build   # musi przejść z 0 TS errors
vercel --prod
```

---

## FAZA 8 — Cleanup Kodu (est. 2-3h)

### Task 8.1: Skonsoliduj 3 API clienty → 1

Zostaw `api-v2.ts` (hooks) jako jedyny client.  
Przenieś `apiFetch` z `api.ts` i `apiRequest` z `api-client.ts` do `api-v2.ts`.  
Usuń `api.ts` i `api-client.ts`.

**Uwaga:** Sprawdź importy — kilka komponentów może importować z tych plików.

### Task 8.2: Napraw redirect w api-client.ts

```tsx
// Obecne (zepsute):
window.location.href = '/auth/login'
// Poprawne:
window.location.href = '/login'
```

### Task 8.3: Usuń dead code w HeroSection

Linia 132: usuń `const reduce = useReducedMotion()` (zmienna nieużywana po CSS rewrite).

### Task 8.4: ScreenshotsSection — CSS fallback

**Plik:** `src/app/landing/LandingClient.tsx`, linia ~524  
`motion.div` z `initial={{ opacity: 0, y: 10 }}` bez fallbacku.

```tsx
// Dodaj id do wrappera i CSS fallback:
<motion.div
  key={activeTab}
  initial={{ opacity: 0, y: 10 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.25 }}
  style={{ animation: 'heroIn 0.4s ease forwards' }}  // CSS fallback
>
```

### Task 8.5: Usuń unsafe-eval z CSP produkcji

**Plik:** `next.config.mjs`
```js
// Obecne:
`script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com`
// Poprawne dla prod (zostaw tylko dla dev):
const isDev = process.env.NODE_ENV === 'development'
`script-src 'self' 'unsafe-inline' ${isDev ? "'unsafe-eval' https://unpkg.com" : ""}`
```

### Task 8.6: Wyczyść legacy assets

```bash
# Usuń B02-B16 i 01-10 z public/brand/ jeśli nieużywane w app/*
# Zostaw: B01, B04, live-*.png, BRAND-BIBLE*.md
```

---

## Kolejność Priorytetów

| Kolejność | Faza | Czas | Impact |
|-----------|------|------|--------|
| 🔥 1 | Faza 1 — Dashboard KPI | 3-4h | Eliminuje najbardziej widoczny mock |
| 🔥 2 | Faza 5 — Mobile landing | 4-6h | Wymagane przed launch |
| 🔥 3 | Faza 7 — DNS + Deploy | 1h | Domena żywa |
| ⚡ 4 | Faza 2 — Zwiad real API | 4-6h | Główna funkcja produktu |
| ⚡ 5 | Faza 6 — SEO & PWA | 2h | Google indexing |
| ⚡ 6 | Faza 3 — Pipeline | 2-3h | Sprzedażowy moduł |
| 🔧 7 | Faza 4 — Bid Intel | 1-2h | Łatwe — odkomenuj TODO |
| 🔧 8 | Faza 8 — Cleanup | 2-3h | Dług techniczny |

**Szacowany czas łączny:** 23-33h pracy agentów (można parallelizować fazy niezależne)

---

## Jak Uruchomić

```bash
# Faza 1-4 i 8: dev server live
pnpm dev --port 3001

# Weryfikacja po każdej fazie:
curl http://localhost:8765/api/v2/dashboard/stats   # backend działa?
curl http://localhost:3001/app                       # frontend 200?
npx tsc --noEmit                                     # 0 TS errors?

# Deploy:
pnpm build && vercel --prod
```
