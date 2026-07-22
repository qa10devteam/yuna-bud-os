---
version: alpha
name: YU-NA BudOS
description: >
  Premium dark SaaS design system dla platformy decyzyjnej w przetargach budowlanych.
  DNA: Linear.app depth (#07070d canvas) × Apple spacing (8px base, negative tracking, pill CTAs) × 
  własny emerald (#10b981) jako jedyny kolor akcentowy. Styl: software-craft documentation —
  gęsty, techniczny, cicho luksusowy. Produkt mówi przez screenshoty, UI schodzi w tle.

colors:
  # Canvas & Surfaces
  canvas: "#07070d"
  surface-1: "#0f1011"
  surface-2: "#141516"
  surface-3: "#1a1a20"
  # Hairlines
  hairline: "#1e1e28"
  hairline-strong: "#2a2a36"
  # Text
  ink: "#f1f5f9"
  ink-muted: "#94a3b8"
  ink-subtle: "#475569"
  ink-tertiary: "#334155"
  # Accent — JEDYNY kolor chromowy w systemie (jak Action Blue u Apple)
  primary: "#10b981"
  primary-glow: "rgba(16,185,129,0.12)"
  primary-border: "rgba(16,185,129,0.25)"
  on-primary: "#07070d"
  # Semantyczne
  success: "#10b981"
  warning: "#f59e0b"
  error: "#ef4444"
  info: "#818cf8"

typography:
  display-xl:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 72px
    fontWeight: 800
    lineHeight: 1.04
    letterSpacing: "-0.04em"
  display-lg:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  display-md:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 36px
    fontWeight: 700
    lineHeight: 1.12
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  body-lg:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.65
    letterSpacing: "0"
  body:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.65
    letterSpacing: "0"
  body-strong:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 15px
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  caption:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  data:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.0
    letterSpacing: "-0.02em"
  nav:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: "0"
  label:
    fontFamily: "Space Grotesk, system-ui, -apple-system, sans-serif"
    fontSize: 11px
    fontWeight: 600
    lineHeight: 1.0
    letterSpacing: "0.1em"

rounded:
  none: 0px
  xs: 5px
  sm: 8px
  md: 10px
  lg: 14px
  xl: 18px
  pill: 9999px
  full: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 64px
  section: 96px

components:
  # Nawigacja
  nav:
    backgroundColor: "rgba(7,7,13,0.8)"
    textColor: "{colors.ink-muted}"
    typography: "{typography.nav}"
    height: 56px
    padding: 0 24px
  # Przyciski — PILL jest kluczową decyzją brandową
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.pill}"
    padding: 12px 24px
  button-primary-hover:
    backgroundColor: "#0ea572"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.pill}"
  button-secondary:
    backgroundColor: transparent
    textColor: "{colors.ink-muted}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: 12px 24px
  # Karty
  card:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 24px
  card-featured:
    backgroundColor: "rgba(16,185,129,0.04)"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 28px
  # Workflow tiles — Apple edge-to-edge alternation
  tile-dark:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: 96px 24px
  tile-surface:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: 96px 24px
  # Hero screenshot
  hero-screenshot:
    rounded: "{rounded.xl}"
    padding: 0
  # Footer
  footer:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink-subtle}"
    typography: "{typography.body}"
    padding: 64px 24px
---

## Overview

YU-NA BudOS to platforma decyzyjna dla wykonawców przetargów budowlanych — nie zwykły SaaS,
ale system intelligence dla firm, gdzie jeden przetarg ma wartość 2–50 mln PLN.

Design musi komunikować: **precyzję, przewagę informacyjną, powagę B2B**. Nie startup-vibe.

**Kluczowe zasady DNA:**
- **Emerald `{colors.primary}` jest jedynym kolorem akcentowym** — nigdzie więcej chroma. Jak Action Blue u Apple.
- **Alternating tiles** (canvas ↔ surface-1) tworzą rytm sekcji. Kolor zmiany = separator.
- **Negatywny letter-spacing przy headline** — "Apple tight", standard premium.
- **JetBrains Mono TYLKO dla danych** — liczby, kody, metryki. Nigdy body copy.
- **Pill buttons** (`{rounded.pill}`) — jedyna forma CTA. Rectangles to generic.
- **Produkt mówi przez screenshoty** — UI schodzi, screenshot wypełnia przestrzeń.

## Colors

### Accent — #10b981
Emerald to jedyny kolor chromowy. Pojawia się na: primary button, live badge, kolor w H1, 
liczby metryk, ikony, status dots. **Nigdzie poza tymi miejscami.**
Na ciemnym tle: glow `{colors.primary-glow}` + border `{colors.primary-border}`.

### Surfaces — głębia bez gradientów
4 poziomy surface (canvas → surface-3) tworzą głębię przez zmianę koloru, nie box-shadow.
Shadow używamy **TYLKO** pod screenshotami produktu (jak Apple product shadow).

### Tekst — 3 poziomy
- `{colors.ink}` (#f1f5f9) — headline, primary copy  
- `{colors.ink-muted}` (#94a3b8) — secondary, nav links, ghost buttons
- `{colors.ink-subtle}` (#475569) — body paragraphs, opisy kart

## Typography

### Zasada negative tracking
Każdy headline ≥ 24px dostaje negative letterSpacing (`-0.015em` do `-0.04em`).
Body copy i caption: neutralne tracking (0 lub minimalne).

### JetBrains Mono — strefa techniczna
Mono tylko dla: liczb metryk, step badges (01/02), cen, kodów, wartości z bazy.
Nigdy dla body copy — to byłoby over-engineering.

### Breakpoints typografii
- Mobile (≤ 640px): display-xl → 42px, display-lg → 32px
- Tablet (641–1023px): display-xl → 56px
- Desktop (≥ 1024px): pełna skala

## Layout

### Apple 8px grid
Base unit 8px. Strukturalne wymiary: 8/16/24/40/64/96.
Section padding: zawsze `{spacing.section}` (96px) vertical.
Card padding: `{spacing.lg}` (24px) lub `{spacing.xl}` (40px) dla featured.

### Alternating tile rhythm
Hero (canvas) → TrustLogos (surface-1) → Workflow tile 1 (canvas) → tile 2 (surface-1) →
tile 3 (canvas) → tile 4 (surface-1) → Metrics (surface-1) → Features (canvas) →
Pricing (canvas) → CTA (canvas + radial glow) → Footer (surface-1).

### Max-width
- Narrow text sections: 640–720px centered
- Standard content: 1120px
- Hero screenshot: 1000px
- Pełna szerokość: tile backgrounds (canvas change)

## Elevation & Depth

| Poziom | Traktowanie | Użycie |
|--------|-------------|--------|
| Flat | Brak shadow, brak border | Full-bleed tiles, nav, footer |
| Hairline | `1px solid {colors.hairline}` | Karty, separatory |
| Hairline-strong | `1px solid {colors.hairline-strong}` | Hover state kart |
| Frosted | `backdrop-filter: blur(20px)` + bg 80% opacity | Nav, floating bars |
| Product shadow | `0 40px 100px rgba(0,0,0,0.6)` | Hero screenshot, produkt na surface |

**Zasada:** shadow tylko pod screenshotami i hero image. Nigdy pod kartami lub buttonami.

## Shapes

Pill (`{rounded.pill}`) jest sygnaturowym kształtem interaktywnym — wszystkie CTA to pill.
Karty: `{rounded.lg}` (14px). Screenshoty: `{rounded.xl}` (18px). Tiles: `{rounded.none}`.

## Components

### Nav
Frosted glass (backdrop-filter blur 20px), bg rgba(7,7,13,0.8), border-bottom hairline,
height 56px. Linki muted → ink on hover. Right: ghost pill "Zaloguj" + emerald pill CTA.

### Hero
Full-width centered layout. Radial emerald glow od góry. Badge pill live status.
H1 display-xl. Subline body-lg max-width 560px. Dwa pill CTA. Stats row JetBrains.
Screenshot max-width 1000px z product shadow.

### Workflow Tiles (Apple alternating)
4 kroki w full-width tiles. Alternating bg (canvas / surface-1). Grid 2-col z reversal.
Step badge JetBrains Mono w surface-2 box. H3 display-md. Body body-lg.

### Metrics Row
Full-bleed surface-1. 4 kolumny. Liczby data (48px JetBrains emerald). Label 16px ink. Sub 12px subtle.

### Bento Grid (Features)
3 kolumny, 1 karta wide (span 2). Karty surface-1, border hairline.
Hover: border-color hairline-strong + translateY(-2px).

## Do's and Don'ts

### Do
- Używaj `{colors.primary}` TYLKO dla interaktywnych elementów i kluczowych danych.
- Ustaw każdy headline ≥ 24px z negative letterSpacing (`-0.015em` minimum).
- Użyj `{rounded.pill}` dla KAŻDEGO buttona — to sygnaturowy shape.
- Alternuj tile backgrounds dla rytmu sekcji — kolor change = divider.
- JetBrains Mono TYLKO dla liczb, kodów, technikaliów.
- Product shadow (`0 40px 100px rgba(0,0,0,0.6)`) TYLKO pod screenshotami.
- Frosted glass nav z backdrop-filter.

### Don't
- Nie dawaj koloru emerald na dekoracje, ikony, które nie są akcją ani danymi.
- Nie używaj box-shadow na kartach lub buttonach.
- Nie mieszaj border-radius — tylko pill dla CTA, lg dla kart.
- Nie używaj gradientów za wyjątkiem radial emerald glow w hero/CTA.
- Nie rób rectangularnych buttonów (borderRadius 8–12px) — to generyk.
- Nie używaj weight 700 dla body — 600 max.
- Nie używaj Tailwind class names.
