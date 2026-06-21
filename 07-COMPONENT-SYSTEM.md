---
title: "Component System Overview"
status: "Final"
---

# COMPONENT SYSTEM OVERVIEW

## 1. FOUNDATION
- **Library:** `shadcn/ui` (Radix UI primitives + Tailwind).
- **Customization:** All components customized to ZIEMIA Design System.
- **No Default State:** Every component has tailored radius, color, shadow.

## 2. COMPONENT LAYERS
1. **Primitives:** Buttons, Inputs, Cards, Modals, Charts, Sliders, Tables, SideMenus, Forms, Navigation, Footers, Headers.
2. **Pattern Components:** TenderCard, CostRow, RiskBadge, DecisionPanel.
3. **Template Sections:** Hero, FeatureGrid, SocialProof, CTA.

## 3. NAMING CONVENTION
- `ZButton`, `ZInput`, `ZCard`, `ZChart`, `ZModal`, `ZNotification`, `ZSlider`, `ZTable`, `ZSideMenu`, `ZForm`, `ZNavigation`, `ZFooter`, `ZHeader`.
- Prefix `Z` for ZIEMIA.

## 4. SHADCN/UI CUSTOMIZATION
- **Radius:** `rounded-xl` (12px) for cards, `rounded-full` for buttons.
- **Shadow:** `shadow-sm` default, `shadow-md` hover. Tinted shadows (no pure black).
- **Border:** `border-neutral-200` default, `border-accent-success` for success states.
- **Focus:** `ring-2 ring-accent-tech` for accessibility.

## 5. RESPONSIVE STRATEGY
- Mobile-first.
- Grid collapses to single column on `< 768px`.
- Navigation becomes hamburger on mobile.
- Tables become scrollable or card-based on mobile.

## 6. ACCESSIBILITY
- WCAG AA compliant.
- Keyboard navigable.
- Screen reader friendly.
- Reduced motion supported.
