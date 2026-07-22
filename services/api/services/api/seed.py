"""Seed script — creates default tenant, owner_profile, sample rate_card, and demo data.

Usage: python -m services.api.seed

Idempotent: safe to run multiple times.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Make packages importable when run as script
for p in [
    str(Path(__file__).parents[3] / "packages" / "shared"),
    str(Path(__file__).parents[3] / "packages" / "db"),
    str(Path(__file__).parents[2]),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import select, text
from terra_db.session import get_session
from terra_db.models import Tenant, OwnerProfile, RateCard

TENANT_ID = os.getenv("DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
OWNER_ID = "00000000-0000-0000-0000-000000000002"

# Demo org / tenant / user constants — must match routers/demo.py
DEMO_TENANT_ID = "c4879c87-016c-4580-b913-212c904c20fd"  # actual tenant_id for demo org
DEMO_ORG_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"     # organisations.id
DEMO_USER_ID = "40a71ef6-d6eb-48a3-b62e-7da3df5f0a17"
DEMO_EMAIL = "demo@terra-os.pl"

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

DEMO_TENDERS = [
    {"title": "Budowa drogi gminnej w miejscowości Kowale", "buyer": "Gmina Kowale",
     "value_pln": 2_450_000, "cpv": ["45233120-6"], "status": "new", "match_score": 0.85},
    {"title": "Remont nawierzchni ul. Lipowej w Strzelinie", "buyer": "Powiat Strzeliński",
     "value_pln": 890_000, "cpv": ["45233220-7"], "status": "new", "match_score": 0.79},
    {"title": "Budowa zbiornika retencyjnego", "buyer": "Gmina Piława Górna",
     "value_pln": 3_200_000, "cpv": ["45247270-3"], "status": "new", "match_score": 0.73},
    {"title": "Termomodernizacja budynku szkoły podstawowej", "buyer": "Gmina Dzierżoniów",
     "value_pln": 1_750_000, "cpv": ["45321000-3"], "status": "new", "match_score": 0.67},
    {"title": "Budowa chodnika wzdłuż DW385", "buyer": "ZDW Dolnośląskiego",
     "value_pln": 420_000, "cpv": ["45233162-2"], "status": "new", "match_score": 0.61},
]


def seed() -> None:
    Session = get_session()
    with Session() as session:
        # ── Default Tenant ────────────────────────────────────────────────────
        tenant = session.get(Tenant, TENANT_ID)
        if not tenant:
            tenant = Tenant(id=TENANT_ID, name="Firma Robót Ziemnych — Maciek K.")
            session.add(tenant)
            print(f"[seed] Created tenant {TENANT_ID}")
        else:
            print(f"[seed] Tenant {TENANT_ID} already exists")

        # ── OwnerProfile ──────────────────────────────────────────────────────
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

        # ── Rate card ─────────────────────────────────────────────────────────
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

        # ── B1-01 FIX: Demo tenant + org + user ───────────────────────────────
        _seed_demo_tenant(session)

        session.commit()

        # ── B1-01/B1-16 FIX: Demo tenders + notifications + gantt + kosztorys ─
        _seed_demo_data_raw(session)

        print("[seed] Done.")


def _seed_demo_tenant(session) -> None:
    """Ensure demo tenant, org and user exist — B1-01 fix."""
    now = datetime.now(timezone.utc)

    # Demo tenant
    demo_tenant = session.get(Tenant, DEMO_TENANT_ID)
    if not demo_tenant:
        demo_tenant = Tenant(id=DEMO_TENANT_ID, name="Demo Sp. z o.o.")
        session.add(demo_tenant)
        print(f"[seed] Created demo tenant {DEMO_TENANT_ID}")

    # Demo organisation (ec3d1e16) — must have tenant_id=DEMO_TENANT_ID
    row = session.execute(
        text("SELECT id FROM organizations WHERE id = :id"),
        {"id": DEMO_ORG_ID},
    ).fetchone()
    if not row:
        session.execute(
            text(
                "INSERT INTO organizations (id, name, plan, tenant_id, created_at) "
                "VALUES (:id, 'Demo Sp. z o.o.', 'pro', :tid, :now)"
            ),
            {"id": DEMO_ORG_ID, "tid": DEMO_TENANT_ID, "now": now},
        )
        print(f"[seed] Created demo org {DEMO_ORG_ID}")
    else:
        # Ensure tenant_id is correct
        session.execute(
            text("UPDATE organizations SET tenant_id = :tid WHERE id = :id AND tenant_id IS DISTINCT FROM :tid"),
            {"id": DEMO_ORG_ID, "tid": DEMO_TENANT_ID},
        )

    # Demo user — demo@terra-os.pl
    # Robust upsert: handle cases where id or email already exist independently
    import bcrypt as _bcrypt
    pw_hash = _bcrypt.hashpw(b"BudOS2026!", _bcrypt.gensalt()).decode()

    # Check what's already in DB
    existing_by_email = session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": DEMO_EMAIL},
    ).fetchone()
    existing_by_id = session.execute(
        text("SELECT email FROM users WHERE id = :id"),
        {"id": DEMO_USER_ID},
    ).fetchone()

    if existing_by_email:
        # Email exists — update in place (may have different id)
        session.execute(
            text(
                "UPDATE users SET name=:name, password_hash=:pw, org_id=:org, "
                "is_active=true WHERE email=:email"
            ),
            {"name": "Demo User", "pw": pw_hash, "org": DEMO_ORG_ID, "email": DEMO_EMAIL},
        )
        print(f"[seed] Updated existing demo user {DEMO_EMAIL}")
    elif existing_by_id:
        # ID taken by deleted/other user — insert with new UUID
        new_id = str(uuid.uuid4())
        session.execute(
            text(
                "INSERT INTO users (id, email, name, password_hash, org_id, role, is_active, created_at) "
                "VALUES (:id, :email, :name, :pw, :org, 'owner', true, :now)"
            ),
            {"id": new_id, "email": DEMO_EMAIL, "name": "Demo User",
             "pw": pw_hash, "org": DEMO_ORG_ID, "now": now},
        )
        print(f"[seed] Created demo user {DEMO_EMAIL} with new id {new_id}")
    else:
        # Clean insert
        session.execute(
            text(
                "INSERT INTO users (id, email, name, password_hash, org_id, role, is_active, created_at) "
                "VALUES (:id, :email, :name, :pw, :org, 'owner', true, :now)"
            ),
            {"id": DEMO_USER_ID, "email": DEMO_EMAIL, "name": "Demo User",
             "pw": pw_hash, "org": DEMO_ORG_ID, "now": now},
        )
        print(f"[seed] Created demo user {DEMO_EMAIL}")

    # Subscription for demo org
    session.execute(
        text(
            "INSERT INTO subscription (org_id, plan, status) "
            "VALUES (:oid, 'pro', 'active') "
            "ON CONFLICT (org_id) DO UPDATE SET plan='pro', status='active'"
        ),
        {"oid": DEMO_ORG_ID},
    )


def _seed_demo_data_raw(session) -> None:
    """Seed demo tenders, notifications, gantt_tasks, kosztorys_items — B1-16 fix."""
    now = datetime.now(timezone.utc)

    # ── Demo tenders (tenant_id=DEMO_TENANT_ID) ───────────────────────────────
    existing_count = session.execute(
        text("SELECT COUNT(*) FROM tender WHERE tenant_id = :tid"),
        {"tid": DEMO_TENANT_ID},
    ).scalar() or 0

    if existing_count == 0:
        for i, td in enumerate(DEMO_TENDERS):
            tender_id = str(uuid.uuid4())
            ext_id = f"DEMO-SEED-{uuid.uuid4().hex[:8].upper()}"
            session.execute(
                text(
                    "INSERT INTO tender "
                    "(id, tenant_id, source, external_id, title, buyer, cpv, "
                    " voivodeship, value_pln, deadline_at, published_at, url, "
                    " status, match_score, match_reason, raw, created_at) "
                    "VALUES "
                    "(:id, :tid, 'bzp', :ext, :title, :buyer, :cpv, "
                    " 'dolnośląskie', :val, :dl, :pub, '', "
                    " :status, :ms, 'Demo seed', '{}'::jsonb, :now)"
                ),
                {
                    "id": tender_id,
                    "tid": DEMO_TENANT_ID,
                    "ext": ext_id,
                    "title": td["title"],
                    "buyer": td["buyer"],
                    "cpv": td["cpv"],
                    "val": td["value_pln"],
                    "dl": now + timedelta(days=30 - i * 5),
                    "pub": now - timedelta(days=i),
                    "status": td["status"],
                    "ms": td["match_score"],
                    "now": now,
                },
            )
        print(f"[seed] Created {len(DEMO_TENDERS)} demo tenders for tenant {DEMO_TENANT_ID}")
    else:
        print(f"[seed] Demo tenders already exist ({existing_count})")

    # ── Demo notifications for demo user ─────────────────────────────────────
    notif_count = session.execute(
        text("SELECT COUNT(*) FROM notifications WHERE org_id = :oid"),
        {"oid": DEMO_ORG_ID},
    ).scalar() or 0

    if notif_count == 0:
        demo_notifs = [
            ("info", "Nowy przetarg dopasowany", "Znaleziono przetarg pasujący do Twojego profilu — CPV 45233120-6"),
            ("warning", "Termin składania ofert zbliża się", "Przetarg 'Budowa drogi gminnej w Kowalach' — deadline za 3 dni"),
            ("success", "Analiza dokumentów zakończona", "Dokumentacja przetargu została przeanalizowana pomyślnie"),
            ("info", "Aktualizacja BZP", "Pobrano 12 nowych ogłoszeń z portalu e-Zamówienia"),
            ("info", "Wycena gotowa", "Kosztorys dla przetargu 'Remont nawierzchni' jest gotowy do przeglądu"),
        ]
        for ntype, ntitle, nbody in demo_notifs:
            session.execute(
                text(
                    "INSERT INTO notifications (id, user_id, org_id, type, title, body, read, created_at) "
                    "VALUES (:id, :uid, :oid, :type, :title, :body, false, :now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "uid": DEMO_USER_ID,
                    "oid": DEMO_ORG_ID,
                    "type": ntype,
                    "title": ntitle,
                    "body": nbody,
                    "now": now,
                },
            )
        print(f"[seed] Created {len(demo_notifs)} demo notifications")
    else:
        print(f"[seed] Demo notifications already exist ({notif_count})")

    # ── Demo gantt_tasks ──────────────────────────────────────────────────────
    # Get first demo tender id
    demo_tender = session.execute(
        text("SELECT id FROM tender WHERE tenant_id = :tid LIMIT 1"),
        {"tid": DEMO_TENANT_ID},
    ).fetchone()

    if demo_tender:
        gantt_count = session.execute(
            text("SELECT COUNT(*) FROM gantt_tasks WHERE tender_id = :tid"),
            {"tid": str(demo_tender[0])},
        ).scalar() or 0

        if gantt_count == 0:
            gantt_items = [
                ("Analiza dokumentacji", 0, 3, 100),
                ("Przygotowanie kosztorysu", 3, 10, 50),
                ("Złożenie oferty", 10, 14, 0),
            ]
            for pos, (name, start_off, end_off, progress) in enumerate(gantt_items):
                session.execute(
                    text(
                        "INSERT INTO gantt_tasks (id, tender_id, name, start_date, end_date, progress, color, position, created_at) "
                        "VALUES (:id, :tid, :name, :sd, :ed, :prog, '#3B82F6', :pos, :now)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tid": str(demo_tender[0]),
                        "name": name,
                        "sd": (now + timedelta(days=start_off)).date(),
                        "ed": (now + timedelta(days=end_off)).date(),
                        "prog": progress,
                        "pos": pos,
                        "now": now,
                    },
                )
            print(f"[seed] Created {len(gantt_items)} demo gantt_tasks")
        else:
            print(f"[seed] Demo gantt_tasks already exist ({gantt_count})")

    # ── Demo estimate + kosztorys items ──────────────────────────────────────
    # Check if demo estimate exists for demo tenant
    est_row = session.execute(
        text("SELECT id FROM estimate WHERE tenant_id = :tid LIMIT 1"),
        {"tid": DEMO_TENANT_ID},
    ).fetchone()

    if not est_row and demo_tender:
        est_id = str(uuid.uuid4())
        session.execute(
            text(
                "INSERT INTO estimate (id, tenant_id, tender_id, variant, total_net_pln, overhead_pct, profit_pct, params, created_at) "
                "VALUES (:id, :tid, :tender_id, 'owner', 0, 15, 10, '{}'::jsonb, :now)"
            ),
            {
                "id": est_id,
                "tid": DEMO_TENANT_ID,
                "tender_id": str(demo_tender[0]),
                "now": now,
            },
        )
        print(f"[seed] Created demo estimate {est_id}")

        # kosztorys items via estimate_line
        items = [
            ("Roboty ziemne — wykop fundamentowy", "m3", 350, 22.0),
            ("Wywóz urobku", "tkm", 1200, 4.2),
            ("Nasyp zagęszczony", "m3", 280, 22.0),
            ("Robocizna drogowa", "m2", 800, 85.0),
            ("Beton C20/25", "m3", 45, 420.0),
        ]
        total = 0.0
        for name, unit, qty, price in items:
            line_total = qty * price
            total += line_total
            session.execute(
                text(
                    "INSERT INTO estimate_line (id, tenant_id, estimate_id, description, unit, quantity, unit_price, line_total_pln, created_at) "
                    "VALUES (:id, :tid, :eid, :desc, :unit, :qty, :price, :total, :now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tid": DEMO_TENANT_ID,
                    "eid": est_id,
                    "desc": name,
                    "unit": unit,
                    "qty": qty,
                    "price": price,
                    "total": line_total,
                    "now": now,
                },
            )
        # Update estimate total
        session.execute(
            text("UPDATE estimate SET total_net_pln = :total WHERE id = :id"),
            {"total": total, "id": est_id},
        )
        print(f"[seed] Created {len(items)} kosztorys items (total: {total:.2f} PLN)")
    elif est_row:
        print(f"[seed] Demo estimate already exists ({est_row[0]})")

    session.commit()


if __name__ == "__main__":
    seed()
