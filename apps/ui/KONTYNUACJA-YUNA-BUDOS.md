# YU-NA BudOS — Plik Kontynuacyjny

**Data audytu:** 2026-07-22  
**Stack:** Next.js 16.2.10 + Tailwind v4 + motion/react + Zustand  
**Domena:** yu-na.io (kupiona, DNS zaparkowany)  
**Repo:** `/home/ubuntu/terra-os/apps/ui`  
**Dev:** port 3001 | **API backend:** port 8000/8765 (FastAPI + PostgreSQL)

---

## Stan Projektu — Podsumowanie

| Obszar | Status | Gotowość prod |
|--------|--------|---------------|
| Landing page | ✅ 11 sekcji, 0 TS errors | 70% |
| Dashboard app | ✅ 22 routes, auth działa | 50% |
| Backend API | ✅ FastAPI działa (port 8765) | 60% |
| Dane | 🟡 ~50% mock, ~50% real API | 50% |
| DNS/Hosting | 🔴 Domena zaparkowana | 0% |
| Mobile | 🔴 Brak responsywności landing | 20% |
| SEO | 🟡 Brak sitemap, robots, og:image URL | 30% |
| PWA | 🟡 Brak ikon PNG 192/512 | 60% |

---

## Architektura

```
Browser → Next.js 16 (port 3001) → rewrite /api/* → FastAPI (port 8765) → PostgreSQL
                                                    
Auth: JWT (access + refresh) via Zustand persist → localStorage
Guard: client-side only (hydration wait → check token → redirect /login)
No middleware.ts — no server-side auth
```

---

## Co Działa

### Landing (`/landing`)
- Hero z prawdziwym screenshotem dashboardu (live-dashboard.png)
- CSS keyframes zamiast Framer Motion (fix na tunel/proxy)
- StatsBar, ProblemSection, FeaturesSection, HowItWorks
- ScreenshotsSection z tab-switcherem (4 live screeny)
- TestimonialsSection, PricingSection (4 plany), FinalCTA, Footer
- NavBar z linkami + CTA

### Dashboard (`/app/*`)
- 22 stron/modułów w 7 sekcjach nawigacji
- Login/register/forgot-password flow
- Zustand store z persist auth
- 3 API clienty (api-v2.ts = primary hooks)
- Moduły z real API: Market Intel, Competitors, Bookmarks, Settings, Buyer CRM (partial)
- Moduły mock: Dashboard KPI, Zwiad, Bid Intelligence, Pipeline (partial)

---

## Krytyczne Problemy do Naprawy

### P0 — Blokery produkcji

| # | Problem | Rozwiązanie |
|---|---------|-------------|
| 1 | **DNS zaparkowany** — yu-na.io wskazuje na dns-parking.com | Zmienić NS na Vercel (ns1.vercel-dns.com) lub dodać CNAME → Vercel |
| 2 | **Brak mobile responsywności** landing — inline styles, 0 breakpointów | Przepisać na Tailwind responsive classes (md:, lg:) |
| 3 | **ScreenshotsSection motion.div** — brak fallback, opacity:0 przez tunel | Dodać CSS fallback jak w hero |

### P1 — Ważne przed launch

| # | Problem | Rozwiązanie |
|---|---------|-------------|
| 4 | Brak `sitemap.ts` | Stworzyć `src/app/sitemap.ts` z /landing, /pricing, /login |
| 5 | Brak `robots.ts` | Stworzyć `src/app/robots.ts` — allow all, sitemap URL |
| 6 | Brak `og:image` URL w metadata | Dodać `metadataBase: new URL('https://yu-na.io')` + images |
| 7 | PWA ikony 192/512 brak plików | Wygenerować z icon.svg → PNG |
| 8 | `unsafe-eval` w CSP | Usunąć z produkcji (zostawić tylko dev) |
| 9 | Dwa `vercel.json` (root + apps/ui) | Ujednolicić — root wystarczy |
| 10 | `NEXT_PUBLIC_API_URL` na produkcji | Ustawić w Vercel env vars |

### P2 — Jakość kodu

| # | Problem | Rozwiązanie |
|---|---------|-------------|
| 11 | 3 API clienty (`api.ts`, `api-v2.ts`, `api-client.ts`) | Skonsolidować do jednego |
| 12 | Dead variable `reduce` w HeroSection | Usunąć |
| 13 | Redirect w `api-client.ts` → `/auth/login` (zła ścieżka) | Zmienić na `/login` |
| 14 | BuyerCRM paduje mock data do real API response | Usunąć hack po backendzie |
| 15 | Bid Intelligence — API call zakomentowany (TODO) | Odkomentować gdy backend ready |
| 16 | 26 nieużywanych obrazów w `public/brand/` | Wyczyścić legacy B02-B16, 01-10 |

---

## Moduły — Status Danych

| Moduł | Route | Dane | Priorytet real API |
|--------|-------|------|-------------------|
| Dashboard | `/app` | 🔴 MOCK | HIGH |
| Zwiad/Przetargi | `/app/zwiad` | 🔴 MOCK | HIGH |
| Pipeline | `/app/pipeline` | 🟡 MIXED | HIGH |
| Silnik AI | `/app/silnik` | 🟡 MIXED | MEDIUM |
| Kosztorys | `/app/kosztorys` | 🟡 MOCK | MEDIUM |
| Bid Intelligence | `/app/bid-intelligence` | 🔴 MOCK | MEDIUM |
| Buyer CRM | `/app/buyer-crm` | 🟡 MIXED | LOW (działa) |
| Market Intel | `/app/market-intel` | 🟢 REAL | — |
| Competitors | `/app/competitors` | 🟢 REAL | — |
| Bookmarks | `/app/bookmarks` | 🟢 REAL | — |
| Settings | `/app/settings` | 🟢 REAL | — |
| Kontrakty | `/app/contracts` | 🟡 MOCK | LOW |
| Dokumenty | `/app/documents` | 🟡 MOCK | LOW |
| Oferta | `/app/oferta` | 🟡 MOCK | LOW |

---

## Design System (Tailwind v4 tokens)

```
Kolory:
  ink-950..ink-500: #050508 → #2e2e42 (dark backgrounds)
  em/em-light: #10b981 (emerald accent — primary)
  score: #818cf8 (indigo — scoring)
  go/nogo/warn: green/red/amber (status)
  gold: #d4a843 (premium)

Fonty:
  Display + Body: Space Grotesk
  Mono: JetBrains Mono

Animacje:
  Hero: CSS keyframes (anim-hero-0..4, anim-hero-right)
  Sekcje niżej: Framer Motion Reveal (useInView + 1.2s timeout fallback)
  Utility: float, scan-line, border-pulse, glow-pulse, marquee
```

---

## Deployment Plan

### Krok 1: DNS (5 min)
```
1. Zaloguj się do registrar yu-na.io
2. Zmień NS na: ns1.vercel-dns.com, ns2.vercel-dns.com
3. LUB dodaj CNAME: @ → cname.vercel-dns.com
```

### Krok 2: Vercel Deploy (15 min)
```bash
# W root /home/ubuntu/terra-os:
vercel --prod
# Env vars w Vercel dashboard:
#   NEXT_PUBLIC_API_URL = https://api.yu-na.io (lub EC2 IP)
```

### Krok 3: Backend na EC2 (już działa)
```
FastAPI na port 8765 — potrzebuje public URL
Opcje:
  A) Cloudflare Tunnel → stały subdomain api.yu-na.io
  B) nginx reverse proxy na EC2 + Let's Encrypt
  C) Vercel rewrites → EC2 public IP
```

### Krok 4: Mobile fix (2-4h pracy)
```
Przepisać landing inline styles → Tailwind responsive:
  - Hero grid: grid-cols-1 lg:grid-cols-[1fr_1.15fr]  ← DONE
  - Features: grid-cols-1 md:grid-cols-2 lg:grid-cols-3
  - Pricing: flex-col md:flex-row
  - Stats: grid-cols-2 md:grid-cols-4
  - Typography: text-3xl md:text-5xl
```

---

## Performance Notes

| Metryka | Wartość |
|---------|---------|
| Static JS | 4.0 MB (130 chunks) → ~1.2 MB gzip |
| Largest chunk | 372 KB (prawdopodobnie recharts) |
| Fonts | 3 Google Fonts (~200 KB) |
| Images | unoptimized (CDN powinien obsłużyć) |
| Compression | ✅ enabled |
| Cache | ✅ immutable /_next/static, 7d icons |

---

## Komendy Quick Reference

```bash
# Dev
cd /home/ubuntu/terra-os/apps/ui
pnpm dev --port 3001

# Build
pnpm build

# Tunel (dev preview)
cloudflared tunnel --url http://localhost:3001 --no-autoupdate

# TypeScript check
npx tsc --noEmit

# Login credentials
# demo@terra-os.pl / BudOS2026!

# API backend
cd /home/ubuntu/terra-os && .venv/bin/python3.12 -m uvicorn ...  # port 8765
```

---

## Następne Kroki (priorytet)

1. **DNS** — odklepać yu-na.io → Vercel
2. **Mobile landing** — Tailwind responsive rewrite
3. **SEO pack** — sitemap.ts + robots.ts + og:image + metadataBase
4. **PWA ikony** — wygenerować 192/512 PNG
5. **ScreenshotsSection** — CSS fallback dla motion.div
6. **Mock → Real** — Dashboard, Zwiad, Pipeline (wymaga backend endpoints)
7. **API consolidation** — jeden client zamiast trzech
8. **CSP cleanup** — usunąć unsafe-eval z prod headers
9. **Bundle split** — zbadać 372KB chunk (recharts?)
10. **Prod deploy** — Vercel + backend tunnel/nginx

---

*Plik wygenerowany automatycznie przez audit pipeline (3 agenty równoległe).*
*Użyj tego pliku jako kontekst w nowym wątku: "Kontynuujemy YU-NA BudOS — oto plik kontynuacyjny: [wklej lub załącz]"*
