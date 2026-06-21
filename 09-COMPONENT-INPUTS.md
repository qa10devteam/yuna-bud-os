---
title: "Inputs"
status: "Final"
---

# COMPONENT: ZINPUT

## 1. VARIANTS
- `text`: Standard text input.
- `number`: Numeric input with up/down arrows.
- `search`: Search bar with icon.
- `select`: Dropdown selector.
- `checkbox`: Checkbox with label.
- `radio`: Radio button with label.

## 2. STYLING
- `border border-neutral-300 rounded-lg`.
- `focus:border-accent-tech focus:ring-2 focus:ring-accent-tech/20`.
- `placeholder:text-neutral-400`.
- `bg-white dark:bg-neutral-800`.

## 3. STATES
- `default`: Standard.
- `hover`: Border color darkens.
- `focus`: Accent ring.
- `error`: `border-accent-warning` + error message below.
- `disabled`: `opacity-50 cursor-not-allowed`.

## 4. LABELS
- Label above input (`label` element).
- Helper text optional (`span` below input).
- Error text below input (`span` below helper).

## 5. RULES
- No placeholder-as-label.
- Helper text concise.
- Error messages actionable.
