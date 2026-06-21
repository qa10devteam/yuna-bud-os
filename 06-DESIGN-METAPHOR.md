---
title: "Design Metaphor: The Shovel"
status: "Final"
---

# DESIGN METAPHOR: THE SHOVEL

## 1. CORE CONCEPT
The **Shovel (Łopata)** symbolizes the construction workflow. It is the tool that starts the job and the tool that finishes it.

## 2. METAPHOR MAPPING

### Handle (Trzonek) — Module 1: ZWIAD
- **Function:** Input, Intake, Reaching Out.
- **Analogy:** The handle is where you grip and direct the shovel. It reaches into the ground (the market) to find what's there.
- **Features:** Tender search, filtering, alerting, document ingestion.
- **UI Representation:** Top section, input fields, search bars, list views.

### Shaft (Kij) — Module 2: KOSZTORYSANT & SILNIK
- **Function:** Transmission, Analysis, Structure.
- **Analogy:** The shaft transfers your force to the blade. It structures the effort. It's the core strength.
- **Features:** Cost calculation, risk analysis, BOQ vs. Project comparison, variable panels.
- **UI Representation:** Middle section, data tables, charts, sliders, comparison views.

### Blade (Łyżka) — Module 3: DECYZJA & MÓZG
- **Function:** Output, Action, Execution.
- **Analogy:** The blade digs, lifts, and moves the earth. It's where the work happens and the result is visible.
- **Features:** Decision dashboard, construction planning, team assignment, daily plans, export.
- **UI Representation:** Bottom section, big CTAs, summary cards, calendar views, action buttons.

## 3. VISUAL LANGUAGE
- **Shovel Gradient:** Vertical gradient from Handle (Top) → Shaft (Middle) → Blade (Bottom).
- **Progress Indicator:** A vertical progress bar styled as a shovel shaft.
- **Icons:** Custom shovel-themed icons for navigation.
- **Micro-interactions:** Hover on buttons feels like "digging in" (press down effect).

## 4. IMPLEMENTATION
- Use `bg-gradient-to-b` from neutral-100 to neutral-600 for main container.
- Accent color (`#00FF94`) highlights the "Blade" section (active actions).
- Warning color (`#FF3300`) highlights risks in the "Shaft" section.
