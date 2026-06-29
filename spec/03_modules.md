# spec/03 — Modules

## Module 1 — Zwiad (tender discovery & analysis) · all tiers

### 1.1 Ingestion → normalize → match
- Scheduler runs `ingest.run` (default daily 06:00 local, also on-demand).
- For each source connector (`spec/05`): pull notices since last watermark, upsert into `tender`
  (idempotent on `(tenant_id,source,external_id)`), store `raw`.
- **CPV + geo filter:** keep tenders whose `cpv ∩ owner_profile.cpv_preferred ≠ ∅` OR cpv prefix in the
  earthworks family (`4511*`,`4512*`,`45233*`, …, configurable list) AND `voivodeship ∈ owner voivodeships`
  (or null + national).
- **Matching/scoring:** `match_score ∈ [0,1]` from a deterministic scorer combining: cpv overlap, value band
  vs owner capacity, deadline feasibility, geo distance, and a local-LLM relevance pass over title+scope
  (router → Ollama). `match_reason` is a short Polish rationale. Scoring weights in config; **the score is
  deterministic given inputs** (LLM pass returns a bounded sub-score, not the final number).

**Acceptance M1:** given fixture notices, ingestion upserts the right rows, filter drops out-of-CPV/geo,
`/tenders` returns items ordered by `match_score` desc; re-running ingestion is idempotent (no dupes).

### 1.2 Document pipeline (see spec/05 for parsers)
- On `/tenders/{id}/analyze`: download docs (SWZ/design/STWiOR/przedmiar) to local FS, classify `kind`,
  parse text (pymupdf) or VLM-OCR (Gemma) for scans, extract `przedmiar_item[]`, chunk+embed into
  `document_chunk`.
**Acceptance:** sample tender with a scanned przedmiar yields ≥N parsed `przedmiar_item` rows with
units/quantities and page provenance; low-confidence extractions are flagged, not dropped.

### 1.3 Analysis (Agentic RAG)
- Produce `analysis.summary_md` (plain Polish), `red_flags[]` (contractor-relevant: onerous clauses,
  penalties, short deadlines, unusual warranties), and **discrepancies** via the decision engine (§04).
- Red-flags and summary are LLM-generated but **every red-flag must cite provenance**; unsupported claims
  are dropped.
**Acceptance:** analysis returns summary + ≥1 cited red-flag on a fixture with a known onerous clause;
no red-flag lacks provenance.

### 1.4 Tracker agent
- `/tenders/{id}/watch` starts a durable agent that re-checks the source for deadline/version changes and
  raises notifications. Pausable/resumable. Writes audit entries.

### 1.5 Auto-fill (Tier 2+)
- Prepare tender forms / declarations (JEDZ-style) from `owner_profile`. Output is a **draft**; submission is
  **gated** (`202 approval_id`). Never submits autonomously.

---

## Module 2 — Kosztorysant (estimator) · Tier 1 MVP, Tier 2+ full

### 2.1 Two variants, always both
- **Variant A (doc):** simplified calc `Wk = Σ(Lj × Cj)` per Rozp. MRiT 20.12.2021. `Cj` from market price
  base (config-provided) or KNR priors mapped from `knr_code`. Mirrors the buyer's estimate.
- **Variant B (owner):** detailed calc `Cj = Σ(n×c) + Kpj + Zj` using `rate_card` (RMS rates, efficiencies)
  + `calibration_coeff`. **Computed in deterministic local code; never sent to any cloud LLM.**
- `compare` returns `delta_pln` and `margin_headroom_pct = (A_total − B_total)/A_total`.
**Acceptance:** for a fixture przedmiar + rate_card, both variants compute; line totals sum exactly to
`total_net_pln` (sum-reconciliation test, zero tolerance on rounding policy); compare returns correct delta.

### 2.2 Interactive editing (Tier 2+)
- **Variable sidebar:** `PATCH /estimates/{id}/params` changes variables (overhead %, profit %, efficiency
  multipliers, unit overrides) and recomputes deterministically; each change audited.
- **Chat-brain edits:** `/estimates/{id}/chat` (SSE) — the LLM proposes a structured edit (`{op, target, value}`)
  which is **applied by deterministic code**, then recomputed. The LLM never writes totals directly.
**Acceptance:** a chat instruction "podnieś narzut do 12%" results in a structured param change + recompute;
totals reconcile; an audit row records the change.

### 2.3 Live documentation-rule violations (Tier 2+)
- `/tenders/{id}/rules/check` runs L1 documentary/regulatory axioms against the current estimate + tender
  constraints (e.g., abnormally-low-price ≥30% below buyer estimate). Returns `Flag[]`.

### 2.4 Email-broker agent (Tier 2+)
- For owner-out-of-scope items (e.g. "plac zabaw"): compose RFQs to `counterparties[]`, **gated send**,
  then watch IMAP for replies (idempotent on `message_uid`), parse offers (`parsed_offer`), surface to owner.
- All RFQ tables live in the main Postgres (the "own SQL"). No separate DB server.
**Acceptance:** RFQ creation returns `approval_id`; after approval, send is recorded; a fixtured inbound
reply is parsed into `parsed_offer` and linked to the RFQ.

---

## Module 3 — Mózg (resource-aware management) · Tier 3 only

### 3.1 Registries
- CRUD for `resource_equipment`, `employee`, `competency`, `availability`, `contract` (won tender → delivery).

### 3.2 Logistics optimization
- `/logistics/optimize` builds an OR-Tools MILP: assign equipment+crew to contracts/days respecting
  availability, competency, and equipment capacity; minimize transport cost / idle time. Output:
  `assignments[]` + `routes[]`. Deterministic given inputs; infeasible → explained, not silently empty.
**Acceptance:** a fixture with 2 contracts / 7 employees / limited excavators yields a feasible assignment
respecting availability; an over-constrained fixture returns `engine_infeasible` with a reason.

### 3.3 Daily plan + dispatch
- `POST /plans` assembles: location photos, technical drawings (if present in tender docs), Google Maps pin
  (`lat,lng`), doc-derived cautions (`cautions_md`), boss note.
- `POST /plans/{id}/dispatch` → **gated**; on approval, sends to selected crew via **mobile app push**
  (primary, Tier 3) and/or messenger (secondary). Records `dispatch` rows + audit.
**Acceptance:** a plan dispatch returns `approval_id`; after approval, `dispatch` rows are created per
recipient and the mobile endpoint `/mobile/plans` returns the plan for that employee's device.

### 3.4 Learning loop
- On contract close, compare estimated vs actual quantities/costs → Bayesian update of `calibration_coeff`
  (deterministic; **no LLM**). Versioned. Subsequent variant-B estimates use updated coefficients.
**Acceptance:** feeding a closed contract updates `calibration_coeff` (version increments) and changes a
re-run variant-B estimate in the expected direction.
