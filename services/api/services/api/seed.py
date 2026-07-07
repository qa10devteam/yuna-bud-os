"""Seed script — creates default tenant, owner_profile, and sample rate_card.

Usage: python -m services.api.seed

Idempotent: safe to run multiple times.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# Make packages importable when run as script
for p in [
    str(Path(__file__).parents[3] / "packages" / "shared"),
    str(Path(__file__).parents[3] / "packages" / "db"),
    str(Path(__file__).parents[2]),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import select
from terra_db.session import get_session
from terra_db.models import Tenant, OwnerProfile, RateCard

TENANT_ID = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
OWNER_ID = "00000000-0000-0000-0000-000000000002"

SAMPLE_RATES = [
    {"key": "robocizna_ziemna_m3", "unit": "m3", "rate_pln": 18.50, "source": "knr_prior"},
    {"key": "koparka_gąsienicowa_m3", "unit": "m3", "rate_pln": 9.80, "efficiency": 120.0, "source": "knr_prior"},
    {"key": "wywóz_ziemi_km", "unit": "tkm", "rate_pln": 4.20, "source": "market"},
    {"key": "nasyp_zagęszczony_m3", "unit": "m3", "rate_pln": 22.00, "source": "knr_prior"},
    {"key": "odwodnienie_mb", "unit": "mb", "rate_pln": 85.00, "source": "market"},
    # Multi-sector rate cards (refactor: full construction industry)
    {"key": "robocizna_budowlana_h",   "unit": "h",   "rate_pln": 45.00, "source": "gus_prior"},
    {"key": "robocizna_drogowa_m2",    "unit": "m2",  "rate_pln": 85.00, "source": "gus_prior"},
    {"key": "robocizna_kubatura_m2",   "unit": "m2",  "rate_pln": 120.00, "source": "gus_prior"},
    {"key": "robocizna_instalacje_m",  "unit": "m",   "rate_pln": 95.00, "source": "gus_prior"},
    {"key": "beton_c20_25_m3",         "unit": "m3",  "rate_pln": 420.00, "source": "gus_prior"},
    {"key": "stal_zbrojeniowa_t",      "unit": "t",   "rate_pln": 4800.00, "source": "gus_prior"},
    {"key": "asfalt_beton_t",          "unit": "t",   "rate_pln": 580.00, "source": "gus_prior"},
]


def seed() -> None:
    Session = get_session()
    with Session() as session:
        # Tenant
        tenant = session.get(Tenant, TENANT_ID)
        if not tenant:
            tenant = Tenant(id=TENANT_ID, name="Firma Robót Ziemnych — Maciek K.")
            session.add(tenant)
            print(f"[seed] Created tenant {TENANT_ID}")
        else:
            print(f"[seed] Tenant {TENANT_ID} already exists")

        # OwnerProfile
        owner = session.get(OwnerProfile, OWNER_ID)
        if not owner:
            owner = OwnerProfile(
                id=OWNER_ID,
                tenant_id=TENANT_ID,
                company_name="FRZ Maciek K. Dzierżoniów",
                cpv_preferred=["45111200-7", "45112000-9", "45112100-6", "45233120-6", "45233200-8"],
                voivodeships=["dolnoslaskie", "slaskie", "opolskie", "lubuskie"],
                equipment=[
                    {"type": "koparka_gąsienicowa", "model": "Komatsu PC210", "count": 1},
                    {"type": "koparka_kołowa", "model": "Volvo EC140", "count": 1},
                    {"type": "samochód_samowyładowczy", "model": "MAN TGS 8x4", "count": 3},
                    {"type": "zagęszczarka_płytowa", "model": "Bomag BPR 70/70D", "count": 2},
                    {"type": "walec_wibracyjny", "model": "Hamm HD 10 VV", "count": 1},
                ],
                scope_notes="Roboty budowlane: kubatura, sieci, drogi. Działa na przetargach publicznych.",
            )
            session.add(owner)
            print(f"[seed] Created owner_profile {OWNER_ID}")

        # Rate card
        for r in SAMPLE_RATES:
            existing = session.execute(
                select(RateCard).where(
                    RateCard.tenant_id == TENANT_ID,
                    RateCard.key == r["key"],
                    RateCard.valid_from == None,  # noqa: E711
                )
            ).scalar_one_or_none()
            if not existing:
                rc = RateCard(
                    id=str(uuid.uuid4()),
                    tenant_id=TENANT_ID,
                    key=r["key"],
                    unit=r.get("unit"),
                    rate_pln=r["rate_pln"],
                    efficiency=r.get("efficiency"),
                    source=r.get("source", "market"),
                )
                session.add(rc)
                print(f"[seed] Rate card: {r['key']} = {r['rate_pln']} PLN/{r.get('unit', '?')}")

        session.commit()
        print("[seed] Done.")


if __name__ == "__main__":
    seed()
