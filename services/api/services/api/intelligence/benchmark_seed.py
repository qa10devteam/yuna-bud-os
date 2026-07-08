"""Benchmark Seed — wypełnij cpv_regional_benchmark z market_results.

Agreguje 2504 wyniki przetargów per CPV5 × kwartał → p25/p50/p75/avg.
Następnie dołącza stawki ICB (R/M/S) z icb_ceny_srednie per bieżący kwartał.
"""
from __future__ import annotations

import logging
from datetime import datetime, date

import sqlalchemy as sa

log = logging.getLogger(__name__)


def seed_cpv_benchmark(engine: sa.Engine, quarter_date: date | None = None) -> dict:
    """Seed cpv_regional_benchmark z market_results.

    Returns: {"inserted": N, "updated": N, "total": N}
    """
    if quarter_date is None:
        today = date.today()
        q = (today.month - 1) // 3 + 1
        quarter_date = date(today.year, (q - 1) * 3 + 1, 1)

    inserted = 0
    updated = 0

    with engine.begin() as conn:
        # Sprawdź ile wierszy market_results
        total_mr = conn.execute(sa.text(
            "SELECT count(*) FROM market_results WHERE winning_price_pln > 0"
        )).scalar()
        log.info(f"market_results z cenami: {total_mr}")

        # Agreguj per CPV5 × quarter
        # CPV w market_results to cpv_codes[1] (8-cyfrowy np. 45000000-7)
        # Wyciągamy pierwsze 5 cyfr jako CPV5
        rows = conn.execute(sa.text("""
            WITH cpv_data AS (
                SELECT
                    LEFT(REGEXP_REPLACE(cpv_codes[1], '[^0-9]', '', 'g'), 5) AS cpv5,
                    winning_price_pln,
                    offers_count,
                    published_at
                FROM market_results
                WHERE cpv_codes IS NOT NULL
                  AND array_length(cpv_codes, 1) > 0
                  AND winning_price_pln > 0
                  AND winning_price_pln < 1000000000
            )
            SELECT
                cpv5,
                count(*) AS n_tenders,
                AVG(winning_price_pln)::numeric(18,2) AS avg_value,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY winning_price_pln)::numeric(18,2) AS median_value,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY winning_price_pln)::numeric(18,2) AS p25_value,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY winning_price_pln)::numeric(18,2) AS p75_value,
                MIN(winning_price_pln)::numeric(18,2) AS min_value,
                MAX(winning_price_pln)::numeric(18,2) AS max_value,
                ROUND(AVG(COALESCE(offers_count, 3)), 2) AS avg_offers
            FROM cpv_data
            WHERE LENGTH(cpv5) = 5
            GROUP BY cpv5
            HAVING count(*) >= 2
            ORDER BY count(*) DESC
        """)).fetchall()

        log.info(f"Znaleziono {len(rows)} grup CPV5")

        for row in rows:
            # Upsert per CPV5 × nuts2='PL' (ogólnopolski) × quarter
            result = conn.execute(sa.text("""
                INSERT INTO cpv_regional_benchmark
                    (cpv5, nuts2_code, quarter, n_tenders, n_completed,
                     avg_value, median_value, p25_value, p75_value,
                     min_value, max_value, avg_offers, computed_at)
                VALUES
                    (:cpv5, 'PL', :quarter, :n, :n,
                     :avg, :med, :p25, :p75,
                     :min, :max, :avg_off, NOW())
                ON CONFLICT (cpv5, nuts2_code, quarter)
                DO UPDATE SET
                    n_tenders    = EXCLUDED.n_tenders,
                    n_completed  = EXCLUDED.n_completed,
                    avg_value    = EXCLUDED.avg_value,
                    median_value = EXCLUDED.median_value,
                    p25_value    = EXCLUDED.p25_value,
                    p75_value    = EXCLUDED.p75_value,
                    min_value    = EXCLUDED.min_value,
                    max_value    = EXCLUDED.max_value,
                    avg_offers   = EXCLUDED.avg_offers,
                    computed_at  = NOW()
                RETURNING (xmax = 0) AS was_inserted
            """), {
                "cpv5": row.cpv5,
                "quarter": quarter_date,
                "n": int(row.n_tenders),
                "avg": float(row.avg_value),
                "med": float(row.median_value),
                "p25": float(row.p25_value),
                "p75": float(row.p75_value),
                "min": float(row.min_value),
                "max": float(row.max_value),
                "avg_off": float(row.avg_offers),
            })
            was_ins = result.fetchone()
            if was_ins and was_ins[0]:
                inserted += 1
            else:
                updated += 1

        # Wzbogać o stawki ICB robocizny (R) per CPV → branża budowlana Q2/2026
        icb_r_avg = conn.execute(sa.text("""
            SELECT AVG(cena_netto) FROM icb_ceny_srednie
            WHERE typ_rms = 'R' AND kwartalrok = 2026 AND kwartalnr = 2
        """)).scalar()

        icb_m_avg = conn.execute(sa.text("""
            SELECT AVG(cena_netto) FROM icb_ceny_srednie
            WHERE typ_rms = 'M' AND kwartalrok = 2026 AND kwartalnr = 2
        """)).scalar()

        icb_s_avg = conn.execute(sa.text("""
            SELECT AVG(cena_netto) FROM icb_ceny_srednie
            WHERE typ_rms = 'S' AND kwartalrok = 2026 AND kwartalnr = 2
        """)).scalar()

        if icb_r_avg:
            conn.execute(sa.text("""
                UPDATE cpv_regional_benchmark
                SET icb_r_rate = :r, icb_m_rate = :m, icb_s_rate = :s
                WHERE quarter = :q AND nuts2_code = 'PL'
            """), {
                "r": float(icb_r_avg),
                "m": float(icb_m_avg or 0),
                "s": float(icb_s_avg or 0),
                "q": quarter_date,
            })

    total = inserted + updated
    log.info(f"Benchmark seed: inserted={inserted}, updated={updated}, total={total}")
    return {"inserted": inserted, "updated": updated, "total": total, "quarter": str(quarter_date)}


def seed_win_probability_data(engine: sa.Engine) -> dict:
    """Seed bid_intelligence z market_results (win rate per CPV5).

    Dane do win probability model — ratio winning_price/estimated_value.
    """
    with engine.begin() as conn:
        count = conn.execute(sa.text("""
            INSERT INTO bid_intelligence
                (tenant_id, tender_id, our_price, estimated_value, win_probability,
                 cpv5, n_competitors, submitted_at)
            SELECT
                tenant_id,
                tender_id,
                winning_price_pln,
                estimated_value_pln,
                CASE WHEN winning_price_pln <= estimated_value_pln * 1.05 THEN 0.8 ELSE 0.3 END,
                LEFT(REGEXP_REPLACE(cpv_codes[1], '[^0-9]', '', 'g'), 5),
                COALESCE(offers_count, 3),
                published_at
            FROM market_results
            WHERE winning_price_pln > 0
              AND estimated_value_pln > 0
              AND cpv_codes IS NOT NULL
              AND array_length(cpv_codes, 1) > 0
            ON CONFLICT DO NOTHING
            RETURNING id
        """)).fetchall()

    return {"seeded": len(count)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from terra_db.session import get_engine
    engine = get_engine()
    r = seed_cpv_benchmark(engine)
    print(f"Benchmark: {r}")
