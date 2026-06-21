---
title: "Typography"
status: "Final"
---

# TYPOGRAPHY: ZIEMIA DESIGN SYSTEM

## 1. FONT FAMILY

### Display (Headlines)
- **Font:** `Space Grotesk` (Sans-serif, geometric, industrial).
- **Why:** Technical feel, high readability, modern but not trendy.
- **Usage:** H1-H3, Section Headers, CTA Labels.
- **Fallback:** `system-ui, -apple-system, sans-serif`.

### Body (UI Text)
- **Font:** `Inter` (Sans-serif, neutral, highly readable).
- **Why:** Standard for UI, accessible, works in all weights.
- **Usage:** Body text, labels, helpers, error messages.
- **Fallback:** `system-ui, -apple-system, sans-serif`.

### Monospace (Numbers/Data)
- **Font:** `JetBrains Mono` (Monospaced, code-friendly).
- **Why:** Engineering aesthetic, aligns numbers perfectly, feels technical.
- **Usage:** Prices, quantities, percentages, dates, code snippets.
- **Fallback:** `monospace`.

## 2. TYPE SCALE

| Element | Size | Weight | Line Height | Tracking | Color |
|---------|------|--------|-------------|----------|-------|
| H1 | `text-5xl md:text-6xl` | 700 | 1.1 | -0.02em | `--color-text-primary` |
| H2 | `text-4xl md:text-5xl` | 600 | 1.2 | -0.01em | `--color-text-primary` |
| H3 | `text-2xl md:text-3xl` | 600 | 1.3 | 0em | `--color-text-primary` |
| H4 | `text-xl` | 600 | 1.4 | 0em | `--color-text-primary` |
| Body | `text-base` | 400 | 1.6 | 0em | `--color-text-primary` |
| Small | `text-sm` | 400 | 1.5 | 0em | `--color-text-secondary` |
| Caption | `text-xs` | 500 | 1.2 | 0.05em | `--color-text-tertiary` |
| Mono | `font-mono` | 400 | 1.5 | 0em | `--color-text-primary` |

## 3. TYPOGRAPHY RULES
- **No Serifs by default.** Only if explicitly requested (not for this industrial project).
- **Italic Descender Clearance:** Use `leading-[1.1]` for italic display text with descenders.
- **Emphasis Rule:** Use bold/italic of same family. No mixed-family emphasis.
- **No Oversized H1s:** Headlines max 2 lines. Subtext max 20 words.
