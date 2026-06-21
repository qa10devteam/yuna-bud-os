---
title: "State Management"
status: "Final"
---

# STATE MANAGEMENT

## 1. LIBRARY
- `Zustand`.

## 2. STORES
- `useTenderStore`: Current tender, filters, search.
- `useCostStore`: Cost data, variables, sliders.
- `useRiskStore`: Risks, flags, analysis.
- `useDecisionStore`: Decision data, summary.
- `useConfigStore`: Theme, language, preferences.

## 3. RULES
- Local `useState` for isolated UI.
- Global Zustand for deep prop-drilling.
- No Redux.
- No Context for global state.
