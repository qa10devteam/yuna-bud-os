# PERF_S84 — Performance Analysis: Terra-OS Tender Queries

Generated: 2026-07-10

## Query 1: Tender by match_score DESC (top offers)

```sql
EXPLAIN ANALYZE SELECT id, title, match_score FROM tender ORDER BY match_score DESC LIMIT 50;
```

### Results

```
Limit  (cost=116.19..116.32 rows=50 width=130) (actual time=0.747..0.752 rows=50 loops=1)
  ->  Sort  (cost=116.19..118.52 rows=930 width=130) (actual time=0.744..0.746 rows=50 loops=1)
        Sort Key: match_score DESC
        Sort Method: top-N heapsort  Memory: 42kB
        ->  Seq Scan on tender  (cost=0.00..85.30 rows=930 width=130) (actual time=0.005..0.548 rows=930 loops=1)
Planning Time: 0.697 ms
Execution Time: 0.796 ms
```

### Analysis
- **Scan type**: Seq Scan (sequential scan)
- **Execution time**: 0.796 ms (fast on dev data, ~930 rows)
- **Recommendation**: For production with >50k rows, add index:
  ```sql
  CREATE INDEX CONCURRENTLY ix_tender_match_score ON tender(match_score DESC);
  ```
  Expected improvement: Seq Scan → Index Scan, 10-100x faster for large datasets.

---

## Query 2: Upcoming tender deadlines

```sql
EXPLAIN ANALYZE SELECT id, title, deadline_at FROM tender WHERE deadline_at > now() ORDER BY deadline_at LIMIT 50;
```

### Results

```
Limit  (cost=118.05..118.18 rows=50 width=133) (actual time=0.676..0.681 rows=50 loops=1)
  ->  Sort  (cost=118.05..120.17 rows=846 width=133) (actual time=0.673..0.675 rows=50 loops=1)
        Sort Key: deadline_at
        Sort Method: top-N heapsort  Memory: 41kB
        ->  Seq Scan on tender  (cost=0.00..89.95 rows=846 width=133) (actual time=0.015..0.521 rows=846 loops=1)
              Filter: (deadline_at > now())
              Rows Removed by Filter: 84
Planning Time: 0.720 ms
Execution Time: 0.718 ms
```

### Analysis
- **Scan type**: Seq Scan with Filter
- **Execution time**: 0.718 ms (dev data)
- **Rows removed by filter**: 84 (9% filtered out)
- **Recommendation**: Add partial index for future deadlines:
  ```sql
  CREATE INDEX CONCURRENTLY ix_tender_deadline_future
    ON tender(deadline_at)
    WHERE deadline_at IS NOT NULL;
  ```
  Expected improvement: Seq Scan → Index Scan for time-filtered queries.

---

## Summary

| Query | Scan Type | Exec Time | Rows Scanned | Recommendation |
|-------|-----------|-----------|-------------|----------------|
| match_score ORDER | Seq Scan (top-N heapsort) | 0.796 ms | 930 | Add index on match_score DESC |
| deadline_at FILTER+ORDER | Seq Scan + Filter | 0.718 ms | 930 (84 filtered) | Add partial index on deadline_at |

### Notes
- Current performance is acceptable for development dataset (~930 rows)
- Both queries use top-N heapsort (memory: 41-42kB) — efficient for LIMIT 50
- Production with 100k+ tenders will benefit significantly from the recommended indexes
- Consider running `VACUUM ANALYZE tender;` periodically to keep planner statistics fresh
