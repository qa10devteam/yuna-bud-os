# BudOS / YU-NA — MASTERPLAN DESIGNU
> Wersja: 1.0 | Budżet: 1000 tur | Status: FAZA 0 — audyt

---

## FILOZOFIA

**Jedno zdanie:** Platforma, która wygląda jak gdyby Apple zbudowało SaaS dla budowlanki.

**Trzy zasady:**
1. **Powietrze** — każdy element ma przestrzeń. Nigdy nie pakujemy.  
2. **Szkło** — glassmorphism nie jest efektem. Jest architekturą warstw.  
3. **Typografia rządzi** — headline decyduje o emocji. Reszta tylko wspiera.

---

## SYSTEM DESIGNU (design tokens — single source of truth)

### Kolory
```
BG:        #050508   (głębsza czerń niż obecna — bardziej jak OLED Apple)
Surface 1: rgba(255,255,255,0.03)   — glass card bg
Surface 2: rgba(255,255,255,0.06)   — elevated card
Surface 3: rgba(255,255,255,0.09)   — hover
Border:    rgba(255,255,255,0.08)   — default border
Border+:   rgba(255,255,255,0.14)   — focus/hover border
Accent:    #10b981 (emerald)        — TYLKO CTA i sygnały GO
Text 1:    #f5f5f7  (Apple white)
Text 2:    rgba(255,255,255,0.55)
Text 3:    rgba(255,255,255,0.28)
```

### Glassmorphism — przepis (Appendix C z skill)
```css
backdrop-filter: blur(24px) saturate(180%) contrast(1.05)
background: linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02))
border: 1px solid rgba(255,255,255,0.10)
box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 24px 64px rgba(0,0,0,0.4)
```

### Typografia
```
Font: Space Grotesk (już zainstalowany) — SF Pro analog
Display: 96-128px / tracking -0.04em / weight 700
H1:      64-80px  / tracking -0.03em / weight 700
H2:      48-56px  / tracking -0.03em / weight 600
H3:      32-40px  / tracking -0.02em / weight 600
Body:    17-19px  / tracking 0       / weight 400
Small:   13-15px  / tracking 0.01em  / weight 400
Label:   11px     / tracking 0.18em  / weight 600 / UPPERCASE
```

### Radius
```
Cards:   20px (rounded-2xl)
Buttons: 9999px (rounded-full) — pill only
Inputs:  12px (rounded-xl)
```

### Spacing scale (Apple-like generous)
```
Section gap:  160px (py-40)
Inner:         80px (py-20)
Card padding:  32px (p-8)
```

---

## PIPELINE — 8 FAZ

### FAZA 1 — DESIGN SYSTEM FOUNDATION (10 tur)
**Co:** globals.css + komponenty bazowe  
**Deliverable:** 
- [ ] globals.css — zaktualizowane tokeny (głębsza czerń, glass utilities)
- [ ] `components/ui/GlassCard.tsx` — reużywalny komponent glassmorphism
- [ ] `components/ui/Button.tsx` — pill button, warianty: primary/ghost/danger
- [ ] `components/ui/Badge.tsx` — GO/NO-GO/WARN/SCORE badges
- [ ] `components/ui/Typography.tsx` — Display/H1/H2/Body/Label

### FAZA 2 — LANDING PAGE (20 tur)
**Co:** Przepisanie `/app/(marketing)/page.tsx` — klasa Apple.com  
**Deliverable:**
- [ ] Hero — fullscreen, gigantyczne typo, screenshot BudOS za glass layer
- [ ] Sekcja Zwiad — split screen, live screenshot, tekst lewy/prawy
- [ ] Sekcja Silnik AI — analogicznie
- [ ] Sekcja Kosztorys — full-width screenshot z caption
- [ ] Stats — czyste tile, bez progress barów
- [ ] Cennik — 3 kolumny, glass cards, bez gradientów
- [ ] Final CTA — wielkie typograficzne zdanie
- [ ] Footer — minimalistyczny

### FAZA 3 — MARKETING / PRODUKT PAGE (10 tur)
**Co:** `/app/(marketing)/budos/page.tsx` — strona produktu BudOS  
**Deliverable:**
- [ ] Hero produktu — "BudOS" w 128px
- [ ] Pipeline workflow — sticky scroll stack
- [ ] Feature deep dive — Zwiad / Silnik / Kosztorys jako osobne sekcje
- [ ] Testimonial — glassmorphism quote card
- [ ] FAQ — accordion
- [ ] CTA bottom

### FAZA 4 — NAWIGACJA I LAYOUT APP (10 tur)
**Co:** Shell aplikacji — navbar, sidebar, layout  
**Deliverable:**
- [ ] `/app/app/layout.tsx` (jeśli istnieje) — glass sidebar
- [ ] Top nav — glassmorphism bar, 52px height
- [ ] Mobile nav — bottom bar

### FAZA 5 — DASHBOARD APP (20 tur)
**Co:** Główny ekran platformy po logowaniu  
**Deliverable:**
- [ ] `/app/app/page.tsx` — redesign karty produktów
- [ ] KPI Bar — glass panel, bez progress barów
- [ ] Product cards — glassmorphism, hover physics

### FAZA 6 — MODUŁY CORE (40 tur)
**Co:** Zwiad, Silnik, Kosztorys — redesign interfejsów  
**Deliverable:**
- [ ] Zwiad list view — clean table + glass sidebar filtrów
- [ ] Tender detail — pełnoekranowy layout, glass panels
- [ ] Silnik GO/NO-GO — duże sygnały, typograficznie mocne
- [ ] Kosztorys — form + podgląd glass

### FAZA 7 — MICRO-INTERAKCJE I ANIMACJE (15 tur)
**Co:** Ruch i physics na całej platformie  
**Deliverable:**
- [ ] Page transitions
- [ ] Hover physics na kartach (tilt 3D)
- [ ] Scroll reveals (Motion whileInView)
- [ ] Loading states — skelety glassmorphism

### FAZA 8 — POLISH + QA (10 tur)
**Co:** Finalna weryfikacja, screenshoty, budowanie  
**Deliverable:**
- [ ] Pełny build 0 errors
- [ ] Screenshoty wszystkich widoków
- [ ] Lighthouse audit
- [ ] Aktualizacja OG images

---

## AKTUALNA FAZA: → 1 — DESIGN SYSTEM FOUNDATION

