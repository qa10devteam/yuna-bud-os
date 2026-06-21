---
title: "Dark Mode Protocol"
status: "Final"
---

# DARK MODE PROTOCOL

## 1. STRATEGY
- `dark:` variant in Tailwind.
- Dual-mode by default.
- Respect `prefers-color-scheme`.

## 2. TOKENS
- `surface`: `white` → `#0A0A0A`.
- `text`: `#1A1A1A` → `#E4E4E2`.
- `accent`: `#00FF94` (unchanged).

## 3. RULES
- Test in both modes.
- Maintain contrast.
- No pure black/white.
- No section theme flips.
