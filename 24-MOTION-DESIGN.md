---
title: "Motion Design"
status: "Final"
---

# MOTION DESIGN

## 1. LIBRARY
- `motion/react` (formerly Framer Motion).

## 2. PRINCIPLES
- Motion must be motivated.
- Animate only `transform` and `opacity`.
- Honor `prefers-reduced-motion`.

## 3. ANIMATIONS
- `entry`: Fade in + slide up.
- `hover`: Scale + shadow.
- `click`: Scale down.
- `scroll`: Reveal stagger.

## 4. SPECS
- `duration`: 300ms.
- `ease`: `cubic-bezier(0.16, 1, 0.3, 1)`.
- `delay`: Stagger 50ms.

## 5. RULES
- No `window.addEventListener('scroll')`.
- No `requestAnimationFrame` loops.
- Isolate motion in client-leaf components.
