---
title: "Buttons"
status: "Final"
---

# COMPONENT: ZBUTTON

## 1. VARIANTS
- `primary`: `bg-accent-success text-neutral-600` (Profit/Go).
- `secondary`: `bg-neutral-500 text-neutral-100` (Neutral actions).
- `warning`: `bg-accent-warning text-neutral-100` (Risk/Danger).
- `ghost`: `bg-transparent text-neutral-600 hover:bg-neutral-100`.
- `outline`: `border border-neutral-300 text-neutral-600`.

## 2. SIZES
- `sm`: `h-8 px-3 text-sm`.
- `md`: `h-10 px-4 text-base`.
- `lg`: `h-12 px-6 text-lg`.

## 3. STATES
- `default`: Standard.
- `hover`: `scale-[0.98]` (tactile push).
- `active`: `scale-[0.95]` (press down).
- `disabled`: `opacity-50 cursor-not-allowed`.
- `loading`: Spinner inside, text hidden.

## 4. RULES
- No duplicate CTA intent.
- CTA text fits on one line.
- Contrast passes WCAG AA.
- No white-on-white buttons.
- No wrapped CTAs.

## 5. CODE SKETCH
```tsx
<Button variant="primary" size="lg">
  STARTUJMY
</Button>
```
