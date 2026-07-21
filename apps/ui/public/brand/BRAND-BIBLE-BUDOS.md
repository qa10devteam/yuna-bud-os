# YU-NA | BudOS — Brand Bible v1.0
*Chief Brand Architect — Vertical Edition | July 2026*
*Semantic Core: PRECYZJA · ZWIAD · PRZEWAGA*

---

## ARCHITEKTURA ARCHETYPICZNA

| | |
|---|---|
| **Archetyp Podstawowy** | MĘDRZEC (Sage) 60% |
| **Archetyp Wtórny** | BOHATER (Hero) 40% |
| **Semantic Core** | PRECYZJA · ZWIAD · PRZEWAGA |
| **Cień Sage** | Dogmatyk — mitygacja: reasoning zawsze widoczny (3 powody przy score) |
| **Cień Hero** | Arogant — mitygacja: "twoja przewaga", nie "bez nas przegrasz" |

---

## PALETA KOLORÓW

```css
/* Ink backgrounds — BudOS-specific */
--color-ink-950:  #07070d;   /* page bg */
--color-ink-900:  #0d0d16;   /* card */
--color-ink-800:  #13131e;   /* elevated card */
--color-ink-700:  #1a1a28;   /* hover */
--color-ink-600:  #222232;   /* active */
--color-ink-line: #2a2a3e;   /* borders */

/* BudOS Accent — TYLKO sygnały decyzji */
--color-budos-em:      #10b981;  /* GO, active, link */
--color-budos-em-light:#34d399;  /* hover */
--color-budos-em-bg:   rgba(16,185,129,.06);
--color-budos-em-brd:  rgba(16,185,129,.22);

/* Signals */
--color-budos-go:    #10b981;
--color-budos-nogo:  #ef4444;
--color-budos-warn:  #f59e0b;
--color-budos-score: #818cf8;  /* indigo-400 */
--color-budos-gold:  #d4a843;  /* Enterprise tier */
```

---

## TYPOGRAFIA

| Rola | Font | Reguła |
|---|---|---|
| Display/Brand | Space Grotesk 700-800 | H1, section headers, brand mark |
| UI/Body | Space Grotesk 400-500 | Body, labels, navigation |
| **Dane/Liczby** | **JetBrains Mono 500-600** | **WSZYSTKIE liczby — bez wyjątków** |
| Micro labels | Space Grotesk 600 caps | +0.12em tracking, UPPERCASE |

---

## NAMING

```
YU-NA | BudOS
       ↑
       pipe z spacjami — nie slash, nie dash
       pipe w kolorze emerald #10b981
```

---

## KOMPONENTY UI

### GO/NO-GO Badge
```tsx
// GO
<span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md
  bg-budos-em-bg border border-budos-em-brd
  text-budos-em font-mono text-xs font-semibold tracking-wider uppercase">
  GO
</span>

// NO-GO
<span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md
  bg-red-500/10 border border-red-500/20
  text-red-400 font-mono text-xs font-semibold tracking-wider uppercase">
  NO-GO
</span>
```

### Score Badge
```tsx
<div className="flex items-baseline gap-0.5">
  <span className="font-mono text-3xl font-semibold text-indigo-400">74</span>
  <span className="font-mono text-sm text-slate-500">/100</span>
</div>
```

### Card
```tsx
<div className="bg-ink-900 border border-ink-line rounded-xl p-5
  hover:border-budos-em-brd hover:bg-ink-800
  transition-colors duration-200">
```

### Sidebar
```
Width: 240px (expanded) / 64px (collapsed)
Background: #07070d
Border-right: #2a2a3e
Active item: 2px emerald left bar + bg-ink-800
```

---

## MOTION LANGUAGE

| Akcja | Czas | Easing |
|---|---|---|
| Hover card | 150ms | ease-out |
| Panel/drawer | 300ms | cubic-bezier(0.16,1,0.3,1) |
| GO badge reveal | 500ms | spring |
| Score counter | 800ms | ease-out (budowanie napięcia) |
| Page transition | 200ms | ease |

**Reguła:** Motion = feedback. Nigdy dekoracja.

---

## GŁOS COPYWRITERSKI

- Liczby zawsze konkretne: `784 000 pozycji`, `40 000 PLN`, `93%`
- Zdania: mix 4-słowowych z 25-słowowymi
- Challenger reframe: `"Model nie jest konfigurowany. Jest uczony Twojej firmy."`
- CTA = audyt, nie cena: `bezpłatny audyt → wycena po audycie`
- **ZAKAZ:** innowacyjny, nowoczesny, kompleksowy, rozwiązanie, narzędzie

---

## ASSET INVENTORY — BudOS Edition

| # | Asset | Rozmiar | Model |
|---|---|---|---|
| B01 | App Icon BudOS | square | Nous Nano Banana Pro |
| B02 | Hero Dark | landscape | Nous Nano Banana Pro |
| B03 | Feature: Silnik Dark | landscape | Nous Nano Banana Pro |
| B04 | Social OG Dark | landscape | Nous Nano Banana Pro |

---

## HIERARCHIA BRAND DNA

```
YU-NA (platforma)
  Archetyp: Sage 65% + Ruler 35%
  Semantic: KLAROWNOŚĆ · PRZEWAGA · PRECYZJA
  Paleta: White/Navy/Indigo — light institutional
      │
      └── YU-NA | BudOS (wertykal)
            Archetyp: Sage 60% + Hero 40%
            Semantic: PRECYZJA · ZWIAD · PRZEWAGA
            Paleta: Ink-Navy + Emerald — dark precision tool
            Target: Właściciel firmy budowlanej (PL)
```

---

*Brand Bible v1.0 | YU-NA | BudOS | CBA Output July 2026*
