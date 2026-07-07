"""M1 — CPV + geo filter: drops notices outside scope."""
from __future__ import annotations

from .bzp_connector import _cpv_matches, EARTHWORKS_CPV_PREFIXES, is_construction_scope
from .normalize import TenderIn
from services.engine.l2_stochastic.sector_profiles import detect_sector

# Target voivodeships for the Dzierżoniów-based firm
# Primary: dolnośląskie + neighbours
TARGET_VOIVODESHIPS: set[str] = {
    "dolnośląskie",
    "opolskie",
    "śląskie",
}

# Optional: all Poland mode (when owner_profile.voivodeships is empty)
ALL_POLAND = False


def passes_cpv_filter(tender: TenderIn) -> bool:
    """Return True if tender CPV codes are in construction scope (division 45)."""
    if not tender.cpv:
        return False
    return is_construction_scope(tender.cpv)


def passes_geo_filter(tender: TenderIn, *, target_voivodeships: set[str] | None = None) -> bool:
    """Return True if tender is in target voivodeship (or all-Poland mode)."""
    target = target_voivodeships or TARGET_VOIVODESHIPS
    if not target:  # empty = all Poland
        return True
    if not tender.voivodeship:
        return True  # unknown location — pass (don't drop)
    return tender.voivodeship.lower() in {v.lower() for v in target}


def passes_value_filter(tender: TenderIn) -> bool:
    """Drop clearly out-of-range contracts (>50 mln = likely too large solo)."""
    if tender.value_pln is None:
        return True  # unknown — pass
    return tender.value_pln <= 50_000_000


def get_tender_sector(tender: TenderIn) -> str:
    """Detect and return sector key for a tender based on CPV codes."""
    return detect_sector(tender.cpv or []).key


def apply_filters(
    tenders: list[TenderIn],
    *,
    voivodeships: set[str] | None = None,
) -> tuple[list[TenderIn], list[TenderIn]]:
    """Return (passed, dropped) lists. Each passed tender gets sector_key set."""
    passed: list[TenderIn] = []
    dropped: list[TenderIn] = []
    for t in tenders:
        if not passes_cpv_filter(t):
            dropped.append(t)
            continue
        if not passes_geo_filter(t, target_voivodeships=voivodeships):
            dropped.append(t)
            continue
        if not passes_value_filter(t):
            dropped.append(t)
            continue
        # Assign sector_key via detect_sector
        sector = detect_sector(t.cpv or [])
        if hasattr(t, "__dict__"):
            t.__dict__["sector_key"] = sector.key
        passed.append(t)
    return passed, dropped
