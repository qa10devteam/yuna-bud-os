# spec/04 — Decision engine (axiomatic–stochastic core)

**Invariant:** the LLM proposes candidates and explains verdicts; **L1 + L2 decide.** Output is always
traceable to an axiom and a source. Implement in `services/engine/`.

```
engine/
  l1_symbolic/   asp.py (clingo)  smt.py (z3)  runner.py   axioms/*.lp  axioms/*.smt
  l2_stochastic/ sampler.py  calibrate.py  sensitivity.py
  l3_orchestration/ extract.py  explain.py   # LLM proposes axioms, explains verdict
  facts.py       # build engine facts from przedmiar/design/estimate
  result.py      # EngineResult assembly + provenance
```

## L1 — symbolic

### Facts (from documents/estimate)
Build a fact set per tender, e.g. (ASP):
```prolog
% przedmiar items
item(i123, "wykop", "m3", 1500).
design_has("odwodnienie").             % derived from design/STWiOR retrieval
depth_cm(450). water_table_cm(300). soil_class("III").
estimate_total(810000). buyer_estimate(900000).
overhead_pct(8). profit_pct(6). rms_sum(i123, 700000).
```

### Axiom classes & sample rules
**A. Regulatory** (e.g., abnormally low price):
```prolog
flag(low_price, block, "Cena >30% poniżej szacunku zamawiającego") :-
    estimate_total(E), buyer_estimate(B), E < 0.7 * B.
```
**B. Documentary** (przedmiar↔design coverage, unit coherence):
```prolog
% every przedmiar item must be covered by the design; else flag
flag(missing_in_design, warn, P) :- item(P,_,_,_), not design_covers(P).
% every design work item must appear in przedmiar
flag(missing_in_przedmiar, warn, W) :- design_work(W), not item_for(W,_).
```
**C. Engineering / earthworks** (mass balance, dewatering, shoring):
```prolog
% mass balance must close within tolerance
flag(mass_balance, block, "Bilans mas się nie domyka") :-
    excavation(V), haul(H), backfill(B), embankment(N), transport(T),
    |V - (H + B + N + T)| > tol_mass.
% deeper than water table ⟹ dewatering item required
flag(missing_dewatering, block, "Głębokość poniżej wód gruntowych bez pozycji odwodnienia") :-
    depth_cm(D), water_table_cm(W), D > W, not design_has("odwodnienie").
% depth + soil class ⟹ shoring/sloping must exist
flag(missing_shoring, warn, "Brak pozycji szalowania/skarpowania dla głębokiego wykopu") :-
    depth_cm(D), D > shoring_threshold, not has_item("szalowanie"; "skarpowanie").
```
**D. Economic** (sum reconciliation, non-negativity):
```prolog
flag(sum_mismatch, block, "Suma RMS+narzuty+zysk ≠ wartość pozycji") :-
    line(L, Total), rms(L,R), overhead(L,O), profit(L,Pf), |Total-(R+O+Pf)| > tol_money.
```
Tolerances (`tol_mass`,`tol_money`,`shoring_threshold`, …) are config constants, **VERIFY** with domain expert
in Phase 0.

### Quantitative feasibility (Z3 / SMT)
For numeric checks better expressed arithmetically (mass balance, depth/water, sum closure, non-negativity),
encode as Z3 constraints; UNSAT ⟹ infeasible with the unsat-core mapped back to source items:
```python
s = Solver()
s.add(excavation == haul + backfill + embankment + transport)   # equality within tol
s.add(estimate_total == Sum(line_totals))
s.add(And([lt >= 0 for lt in line_totals]))
# if depth > water_table: require dewatering quantity > 0
s.add(Implies(depth > water_table, dewatering_qty > 0))
if s.check() == unsat:
    core = s.unsat_core()   # → discrepancies with provenance
```

### Axiom storage & "don't guess → flag"
- Axioms persisted in `axiom` table (`class, code, body, test_ref, version`). The runner loads active axioms,
  composes the program, runs clingo/Z3, and emits `discrepancy` rows with `axiom_id` + provenance.
- **Missing fact ⟹ flag, never assume.** If a required fact (e.g., water table) is absent, emit
  `flag(unknown_*, warn, ...)`; do not default it. Enforced by a test per axiom.

**Acceptance L1:** golden fixtures (3 real-ish tenders from Phase 0) produce the expected discrepancy set;
each axiom has a passing unit test (`axiom.test_ref`); a deliberately broken przedmiar triggers the right
flags with correct provenance.

## L2 — stochastic (Tier 2 basic, Tier 3 full)

`sampler.py` runs **constrained Monte Carlo**: draw material prices (mean-reverting), RMS productivity
(empirical + Bayesian posterior from `calibration_coeff`), weather/standstill (seasonal), quantity
uncertainty (propagated from L1 flags). **Samples violating L1 hard constraints are rejected/projected.**
Correlations via Gaussian copula (Tier 3). Output: margin distribution `p10/p50/p90` and
`win_prob_at_price[]`. `sensitivity.py` computes **Sobol** indices (SALib) → `drivers[]`.

```python
result = run_risk(estimate, facts, n=10000, seed=cfg.seed)   # deterministic given seed
# result.margin_p50, result.win_prob_at_price, result.drivers (S1, ST per factor)
```
**Acceptance L2:** deterministic under fixed seed; distribution monotone vs price; Sobol indices sum-consistent;
no sample violates L1 hard constraints.

## L3 — neuro-symbolic orchestration

- `extract.py`: LLM reads design/STWiOR/przedmiar and **proposes candidate axioms/facts** (e.g., "this clause
  implies a dewatering requirement") as structured JSON. Each candidate is **validated by L1** before being
  promoted to a fact/axiom. Unvalidated candidates are discarded (logged).
- `explain.py`: given the L1+L2 verdict, the LLM writes a plain-Polish explanation ("dlaczego ta wycena nie
  kłamie") — strictly a rendering of the verdict; it must reference the same axioms/provenance and must not
  introduce new conclusions. A test asserts the explanation cites only verdict-present axioms.

**Engine result** (`result.py`) assembles `EngineResult` (see spec/02) with `feasible`, `violations[]`,
`risk{}`, `explanation_md`. This single object backs `/engine` and feeds Module 2 (rules/check) and the
go/no-go UI. **No field of it is authored directly by an LLM except `explanation_md`.**
