#!/bin/bash
echo "=== DR Drill ==="
pg_dump -h 127.0.0.1 -U terraos terraos 2>/dev/null | psql -h 127.0.0.1 -U terraos terraos_test 2>&1 | tail -3
TENDERS=$(psql -h 127.0.0.1 -U terraos -d terraos_test -t -c 'SELECT count(*) FROM tender;' 2>/dev/null | tr -d ' ')
echo "DR check: $TENDERS tenders in terraos_test"
