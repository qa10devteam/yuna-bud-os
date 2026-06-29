"""M4 — L1 Symbolic Decision Engine: clingo + Z3.

Architecture:
  1. FactsBuilder   — converts tender/analysis/estimate dicts → ASP facts (integers)
  2. AxiomLoader    — inline corpus + .lp files for DB seeding
  3. ClingoRunner   — runs clingo, collects violations
  4. EngineResult   — structured output with provenance + axiom_id

NOTE: clingo uses integer arithmetic only. All monetary values are in GROSZE (pln×100),
masses/quantities are rounded to integers.

Offline mode: all axioms are defined inline in AXIOM_CORPUS — no DB required.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AXIOMS_DIR = Path(__file__).parent / "axioms"


# ──────────────────────────────────────────────────────────────────────────────
# Output types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Violation:
    """Single constraint violation emitted by L1 engine."""
    axiom_code: str              # e.g. "A001"
    axiom_id: str | None         # DB UUID (None in offline/test mode)
    severity: str                # "block" | "warn" | "info"
    message: str                 # Polish description
    provenance: dict[str, Any]   # {source, field, value, ...}

    def to_dict(self) -> dict[str, Any]:
        return {
            "axiom_code": self.axiom_code,
            "axiom_id": self.axiom_id,
            "severity": self.severity,
            "message": self.message,
            "provenance": self.provenance,
        }


@dataclass
class EngineResult:
    """L1 engine output."""
    feasible: bool
    violations: list[Violation] = field(default_factory=list)
    explanation_md: str = ""    # Only LLM-authored field (placeholder in M4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feasible": self.feasible,
            "violations": [v.to_dict() for v in self.violations],
            "explanation_md": self.explanation_md,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Facts builder
# ──────────────────────────────────────────────────────────────────────────────

def _pln_to_grosze(value: Any) -> int:
    """Convert PLN float to integer grosze (PLN × 100)."""
    try:
        return int(round(float(value or 0) * 100))
    except (TypeError, ValueError):
        return 0


def _qty(value: Any) -> int:
    """Round quantity to integer."""
    try:
        return int(round(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def build_facts(
    *,
    tender: dict[str, Any],
    przedmiar_items: list[dict[str, Any]],
    estimate: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
) -> str:
    """Convert structured inputs to ASP facts (integer-only — clingo constraint).

    Monetary values in grosze (PLN × 100).
    Masses/quantities rounded to integers.
    Booleans as 0/1.
    """
    lines: list[str] = []

    # --- Tender facts ---
    tender_value = _pln_to_grosze(tender.get("value_pln") or 0)
    buyer_estimate = _pln_to_grosze(
        tender.get("buyer_estimate_pln") or tender.get("value_pln") or 0
    )
    lines.append(f"tender_value({tender_value}).")
    lines.append(f"buyer_estimate({buyer_estimate}).")

    # --- Przedmiar aggregates ---
    mass_wykop = 0
    mass_nasyp = 0
    has_odwodnienie = 0

    for it in przedmiar_items:
        desc = str(it.get("description", "")).lower()
        unit = str(it.get("unit", "")).strip().lower()
        qty = _qty(it.get("quantity") or 0)

        # Mass balance tracking (m3 only)
        if unit == "m3":
            if any(k in desc for k in ("wykop", "wykopu", "kopanie", "odcięcie", "urobek")):
                mass_wykop += qty
            if any(k in desc for k in ("nasyp", "zasypanie", "zasypk", "zasypan")):
                mass_nasyp += qty

        # Dewatering detection
        if any(k in desc for k in ("odwodnienie", "pompowanie", "igłofiltr", "drenaż", "przepompowni")):
            has_odwodnienie = 1

    lines.append(f"mass_wykop({mass_wykop}).")
    lines.append(f"mass_nasyp({mass_nasyp}).")
    lines.append(f"has_odwodnienie({has_odwodnienie}).")

    # Excavation depth and terrain wetness from analysis key_facts
    depth_cm = 0  # depth in cm to keep as integer
    is_wet = 0
    if analysis:
        kf = analysis.get("key_facts") or {}
        try:
            depth_cm = int(round(float(kf.get("max_excavation_depth_m") or 0) * 100))
        except (TypeError, ValueError):
            depth_cm = 0
        is_wet = 1 if kf.get("teren_mokry") or kf.get("wet_terrain") else 0
    lines.append(f"excavation_depth_cm({depth_cm}).")  # in cm
    lines.append(f"teren_mokry({is_wet}).")

    # CPV mismatch flag
    cpv_mismatch = 1 if tender.get("cpv_mismatch") else 0
    lines.append(f"cpv_mismatch({cpv_mismatch}).")

    # --- Estimate facts ---
    if estimate:
        est_total = _pln_to_grosze(estimate.get("total_net_pln") or 0)
        lines.append(f"estimate_total({est_total}).")

        est_lines = estimate.get("lines") or []
        est_line_sum = sum(
            _pln_to_grosze(ln.get("line_total_pln") or ln.get("line_total") or 0)
            for ln in est_lines
        )
        lines.append(f"estimate_lines_sum({est_line_sum}).")
        lines.append(f"estimate_line_count({max(1, len(est_lines))}).")
    else:
        lines.append("estimate_total(0).")
        lines.append("estimate_lines_sum(0).")
        lines.append("estimate_line_count(1).")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Axiom corpus (inline — single source of truth, integer arithmetic)
# ──────────────────────────────────────────────────────────────────────────────

AXIOM_CORPUS: dict[str, dict[str, Any]] = {
    "A001": {
        "class": "engineering",
        "description": "Mass balance — wykop ≈ nasyp ± 15%",
        "body": """\
% A001: masa_bilans — masa wykopu ≈ masa nasypu ± 15%
% Only fires when both sides are >0 (earthworks present)
violation("A001", "block",
  "Bilans mas niezgodny: masa wykopu i nasypu roznia sie o ponad 15%",
  "mass_balance") :-
    mass_wykop(W), mass_nasyp(N),
    W > 0, N > 0,
    D = W - N, D >= 0,
    100 * D > 15 * W.

violation("A001", "block",
  "Bilans mas niezgodny: masa wykopu i nasypu roznia sie o ponad 15%",
  "mass_balance") :-
    mass_wykop(W), mass_nasyp(N),
    W > 0, N > 0,
    D = N - W, D > 0,
    100 * D > 15 * W.
""",
    },
    "A002": {
        "class": "engineering",
        "description": "Odwodnienie — wykop >1.5m AND teren mokry → musi być pozycja odwodnienia",
        "body": """\
% A002: odwodnienie — wykop >150cm AND teren mokry → wymagana pozycja odwodnienia
% excavation_depth_cm > 150 means depth > 1.5m
violation("A002", "block",
  "Brak pozycji odwodnienia: wykop gleboki (>1.5m) na terenie mokrym",
  "brak_odwodnienia") :-
    excavation_depth_cm(D), D > 150,
    teren_mokry(1),
    has_odwodnienie(0).
""",
    },
    "A003": {
        "class": "economic",
        "description": "Cena rynkowa — cena jednostkowa w normie rynkowej",
        "body": """\
% A003: cena rynkowa — placeholder (full SEKOCENBUD lookup in config)
% In offline mode: no violation emitted (requires external price table)
% violation fires only if explicitly asserted
violation("A003", "warn",
  "Cena jednostkowa kosztorysu wymaga weryfikacji z cennikiem SEKOCENBUD",
  "cena_rynkowa") :- cena_rynkowa_flag(1).
""",
    },
    "A004": {
        "class": "regulatory",
        "description": "PZP abnormal low — oferta ≤ 70% wartości zamawiającego",
        "body": """\
% A004: pzp_abnormal_low — estimate ≤ 70% of buyer's estimate (grosze arithmetic)
violation("A004", "warn",
  "Oferta ponizej 70% wartosci szacunkowej zamawiajacego: ryzyko razaco niskiej ceny (art. 224 PZP)",
  "abnormal_low_price") :-
    estimate_total(E), E > 0,
    buyer_estimate(B), B > 0,
    100 * E < 70 * B.
""",
    },
    "A005": {
        "class": "documentary",
        "description": "Suma zgodność — Σ(pozycje) ≈ total ±1%",
        "body": """\
% A005: suma_zgodnosc — sum of lines vs total_net_pln (1% tolerance, grosze)
violation("A005", "block",
  "Niezgodnosc sumy pozycji z wartoscia tytulowa kosztorysu (odchylenie >1%)",
  "sum_mismatch") :-
    estimate_total(T), T > 0,
    estimate_lines_sum(S), S > 0,
    D = T - S, D > 0,
    100 * D > 1 * T.

violation("A005", "block",
  "Niezgodnosc sumy pozycji z wartoscia tytulowa kosztorysu (odchylenie >1%)",
  "sum_mismatch") :-
    estimate_total(T), T > 0,
    estimate_lines_sum(S), S > 0,
    D = S - T, D > 0,
    100 * D > 1 * T.
""",
    },
    "A006": {
        "class": "documentary",
        "description": "CPV zgodność — CPV ogłoszenia ⊆ zakres robót w STWiOR",
        "body": """\
% A006: cpv_zgodnosc — fires only if cpv_mismatch(1) asserted by facts builder
violation("A006", "warn",
  "Niezgodnosc CPV ogloszenia z zakresem robot w STWiOR",
  "cpv_mismatch") :- cpv_mismatch(1).
""",
    },
}


def write_axiom_files() -> None:
    """Write axiom LP files to disk (idempotent)."""
    AXIOMS_DIR.mkdir(parents=True, exist_ok=True)
    for code, ax in AXIOM_CORPUS.items():
        path = AXIOMS_DIR / f"{code}.lp"
        path.write_text(ax["body"], encoding="utf-8")


# Write on first import
try:
    write_axiom_files()
except Exception:
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Clingo runner
# ──────────────────────────────────────────────────────────────────────────────

def _run_clingo(facts: str, axiom_codes: list[str] | None = None) -> list[Violation]:
    """Run clingo with facts + axioms, return violations."""
    import clingo  # type: ignore[import]

    program = facts + "\n"
    codes = axiom_codes if axiom_codes is not None else list(AXIOM_CORPUS.keys())
    for code in codes:
        if code in AXIOM_CORPUS:
            program += f"\n% --- {code} ---\n" + AXIOM_CORPUS[code]["body"] + "\n"

    violations: list[Violation] = []
    parse_errors: list[str] = []

    def on_message(msg_type: Any, message: str) -> None:
        if "error" in str(msg_type).lower():
            parse_errors.append(message)

    ctl = clingo.Control(["--models=1", "--warn=none"])
    try:
        ctl.add("base", [], program)
        ctl.ground([("base", [])])
    except RuntimeError as exc:
        logger.warning("clingo grounding error: %s\nProgram:\n%s", exc, program[:500])
        return violations

    def on_model(model: clingo.Model) -> None:  # type: ignore[name-defined]
        for sym in model.symbols(shown=True):
            if sym.name == "violation" and len(sym.arguments) == 4:
                args = sym.arguments
                code_str = str(args[0]).strip('"')
                sev = str(args[1]).strip('"')
                msg = str(args[2]).strip('"')
                fld = str(args[3]).strip('"')
                violations.append(Violation(
                    axiom_code=code_str,
                    axiom_id=None,
                    severity=sev,
                    message=msg,
                    provenance={"source": "l1_symbolic", "field": fld},
                ))

    ctl.solve(on_model=on_model)
    return violations


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def run_l1(
    *,
    tender: dict[str, Any],
    przedmiar_items: list[dict[str, Any]],
    estimate: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    axiom_codes: list[str] | None = None,
) -> EngineResult:
    """Run L1 symbolic engine.

    Args:
        tender: tender dict (value_pln, buyer_estimate_pln, voivodeship, …)
        przedmiar_items: list of item dicts with description/unit/quantity
        estimate: estimate dict with total_net_pln + lines[] (each with line_total_pln)
        analysis: analysis dict with key_facts{max_excavation_depth_m, teren_mokry}
        axiom_codes: limit to specific axioms (None = all)

    Returns:
        EngineResult with feasible flag + violations list
    """
    facts = build_facts(
        tender=tender,
        przedmiar_items=przedmiar_items,
        estimate=estimate or {},
        analysis=analysis or {},
    )
    logger.debug("L1 facts:\n%s", facts)

    violations = _run_clingo(facts, axiom_codes=axiom_codes)

    # Feasible = no BLOCK violations
    block_viols = [v for v in violations if v.severity == "block"]
    feasible = len(block_viols) == 0

    return EngineResult(
        feasible=feasible,
        violations=violations,
        explanation_md="",
    )
