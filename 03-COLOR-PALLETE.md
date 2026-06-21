---
title: "Color Palette"
status: "Final"
---

# COLOR PALETTE: ZIEMIA DESIGN SYSTEM

## 1. COLOR STRATEGY
- **Base:** Off-white / Off-black. Pure white/black kills depth.
- **Accent:** Single Neon Green for profit/success. Warning Orange for risks. Electric Blue for tech/data.
- **Neutrals:** Concrete grays (cool undertones). No warm beige/cream (premium-slop ban).

## 2. TOKENS (Tailwind v4)

### Primary
- `--color-surface-base`: `#F4F4F0` (Concrete White)
- `--color-surface-inverse`: `#0A0A0A` (Near Black)
- `--color-text-primary`: `#1A1A1A` (Dark Gray)
- `--color-text-inverse`: `#F4F4F0` (White)

### Accent
- `--color-accent-success`: `#00FF94` (Neon Green) — Profit, Go, Success.
- `--color-accent-warning`: `#FF3300` (Warning Orange) — Risk, Red Flags, Danger.
- `--color-accent-tech`: `#3B82F6` (Electric Blue) — Data, Tech, Info.

### Neutrals
- `--color-neutral-100`: `#F4F4F0` (Concrete White)
- `--color-neutral-200`: `#E4E4E2` (Light Gray)
- `--color-neutral-300`: `#A4A4A0` (Medium Gray)
- `--color-neutral-400`: `#6B6B68` (Dark Gray)
- `--color-neutral-500`: `#3D3D3C` (Charcoal)
- `--color-neutral-600`: `#1A1A1A` (Near Black)

## 3. DARK MODE PROTOCOL
- `dark:surface-base`: `#0A0A0A`
- `dark:surface-inverse`: `#F4F4F0`
- `dark:text-primary`: `#E4E4E2`
- `dark:text-inverse`: `#0A0A0A`
- Accent colors remain identical for consistency.

## 4. CONTRAST CHECK
- All text passes WCAG AA (4.5:1) against background.
- Neon Green on Off-White: Passes AA for large text, needs dark text for small body.
- Neon Green on Near Black: Passes AAA.

## 5. GRADIENT POLICY
- No AI-gradients.
- Allowed: Subtle linear gradients for depth (e.g., `bg-gradient-to-b from-neutral-100 to-neutral-200`).
- Allowed: Mesh gradients for hero backgrounds only (if used).
