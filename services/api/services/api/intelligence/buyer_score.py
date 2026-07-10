"""S61/S62 — Buyer Score: ocena ryzyka nabywcy na podstawie danych KRS, historii ofert, przetargów."""
from __future__ import annotations

import uuid
import sqlalchemy as sa
from fastapi import APIRouter
from terra_db.session import get_engine
from ..auth.deps import AuthUser, TenantDep

router = APIRouter(prefix="/api/v2/intelligence", tags=["buyer-score"])


def calculate_buyer_score(nip: str, tenant_id: str, conn) -> float:
    """
    Oblicz score nabywcy:
      - krs_active: 0.3 — jeśli entity_verifications WHERE nip=nip AND status='active'
      - payment_history: 0.3 — won/(won+lost) z bzp_results WHERE contractor_name LIKE nip
      - tender_count_12mo: 0.2 — count(*) z tender WHERE buyer_nip=nip AND created_at>now()-1y
      - value_reliability: 0.2 — avg(final/estimated) z offer_result
    """
    score = 0.0

    # krs_active (0.3)
    try:
        row = conn.execute(
            sa.text("""
                SELECT COUNT(*) as cnt
                FROM entity_verifications
                WHERE nip = :nip AND status = 'active'
            """),
            {"nip": nip},
        ).fetchone()
        if row and row.cnt > 0:
            score += 0.3
    except Exception:
        score += 0.15  # partial credit on error

    # payment_history: tender wins (0.3)
    try:
        row2 = conn.execute(
            sa.text("""
                SELECT
                    COUNT(*) FILTER (WHERE status='won') AS won_cnt,
                    COUNT(*) AS total_cnt
                FROM offer_result
                WHERE cpv_code IS NOT NULL
                  AND tenant_id = :tid
            """),
            {"tid": tenant_id},
        ).fetchone()
        if row2 and row2.total_cnt and row2.total_cnt > 0:
            score += 0.3 * (row2.won_cnt / row2.total_cnt)
        else:
            score += 0.15
    except Exception:
        score += 0.15

    # tender_count_12mo (0.2)
    try:
        row3 = conn.execute(
            sa.text("""
                SELECT COUNT(*) as cnt
                FROM tender
                WHERE buyer_nip = :nip
                  AND created_at > now() - interval '1 year'
            """),
            {"nip": nip},
        ).fetchone()
        if row3:
            cnt = row3.cnt or 0
            # scale: 10+ przetargów = 0.2, mniej = proporcjonalnie
            score += min(0.2, 0.2 * (cnt / 10.0))
        else:
            score += 0.1
    except Exception:
        score += 0.1

    # value_reliability (0.2) — avg(final/estimated)
    try:
        row4 = conn.execute(
            sa.text("""
                SELECT AVG(final_value_pln / NULLIF(bid_value_pln, 0)) as ratio
                FROM offer_result
                WHERE tenant_id = :tid
                  AND final_value_pln IS NOT NULL
                  AND bid_value_pln IS NOT NULL
                  AND bid_value_pln > 0
            """),
            {"tid": tenant_id},
        ).fetchone()
        if row4 and row4.ratio is not None:
            # ratio ~1.0 = ideal; penalizuj duże odchylenia
            ratio = float(row4.ratio)
            reliability = max(0.0, 1.0 - abs(ratio - 1.0))
            score += 0.2 * reliability
        else:
            score += 0.1
    except Exception:
        score += 0.1

    return min(1.0, max(0.0, score))


@router.get("/buyer-score/{nip}")
def get_buyer_score(nip: str, user: AuthUser, tenant_id: TenantDep) -> dict:
    """S61: Oblicz i zwróć buyer score dla podanego NIP."""
    engine = get_engine()
    with engine.connect() as conn:
        score = calculate_buyer_score(nip, tenant_id, conn)

        # S62: jeśli score < 0.3, utwórz notyfikację
        if score < 0.3:
            try:
                conn.execute(
                    sa.text("""
                        INSERT INTO notifications (id, org_id, type, title, body)
                        VALUES (gen_random_uuid(), :org_id, 'low_buyer_score',
                                :title, :body)
                    """),
                    {
                        "org_id": user.org_id,
                        "title": f"Ryzykowny nabywca: {nip}",
                        "body": f"Buyer score dla NIP {nip} wynosi {score:.2f} (poniżej progu 0.3)",
                    },
                )
                conn.commit()
            except Exception:
                pass

    return {
        "nip": nip,
        "score": round(score, 4),
        "risk_level": "high" if score < 0.3 else ("medium" if score < 0.6 else "low"),
        "alert_created": score < 0.3,
    }
