#!/usr/bin/env bash
# daily_ingest.sh — Unified BZP + TED + BIP + Geo-Enrichment runner
# Called by terra-ingest.service / terra-ingest.timer (daily 04:00 UTC)
#
# Exit codes:
#   0  — all stages succeeded
#   1  — one or more stages failed (details in log)

set -euo pipefail

LOG=/var/log/terra-ingest.log
PYTHONPATH_INGEST="/home/ubuntu/terra-os/services/api:/home/ubuntu/terra-os:/home/ubuntu/terra-os/packages/db:/home/ubuntu/terra-os/packages/vendor:/home/ubuntu/terra-os/packages/shared"
BIP_DIR="/home/ubuntu/terra-os/services/ingestion"
PYTHON="/home/ubuntu/terra-os/.venv/bin/python3"
TENANT_ID="ec3d1e16-2139-48c2-93b5-ffe0defd606d"

# DB DSN dla bip_connector (--db-dsn arg)
DB_DSN="postgresql://${DB_USER:-terraos}:${DB_PASSWORD:-}@${DB_HOST:-127.0.0.1}:${DB_PORT:-5432}/${DB_NAME:-terraos}"

# ── helpers ──────────────────────────────────────────────────────────────────
ts()  { date '+%Y-%m-%d %H:%M:%S UTC'; }
log() { echo "[$(ts)] $*" | tee -a "$LOG"; }

FAILED=0

log "========================================================"
log "daily_ingest.sh START"
log "========================================================"

# ── Stage 1: BZP + TED ingest via API ────────────────────────────────────────
log "--- Stage 1: BZP + TED ingest (days_back=2, include_ted=true) ---"
BZP_OUT=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "http://localhost:8000/api/v1/ingest/run?days_back=2&include_ted=true" 2>&1) || true

BZP_STATUS=$(echo "$BZP_OUT" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
BZP_BODY=$(echo "$BZP_OUT" | sed '/HTTP_STATUS:/d')

log "BZP+TED response (HTTP $BZP_STATUS): $BZP_BODY"

if [[ "$BZP_STATUS" =~ ^2 ]]; then
    log "BZP+TED ingest: OK"
else
    log "BZP+TED ingest: FAILED (HTTP $BZP_STATUS) — continuing"
    FAILED=1
fi

# ── Stage 2: wait for writes to settle ───────────────────────────────────────
log "--- Waiting 10s for writes to settle ---"
sleep 10

# ── Stage 3: BIP connector ───────────────────────────────────────────────────
log "--- Stage 3: BIP connector (workers=10, max-sites=500) ---"
(
    # Run as module from repo root to resolve relative imports
    cd /home/ubuntu/terra-os
    export PYTHONPATH="$PYTHONPATH_INGEST"
    export DEFAULT_TENANT_ID="$TENANT_ID"
    export DB_HOST="${DB_HOST:-127.0.0.1}"
    export DB_PORT="${DB_PORT:-5432}"
    export DB_NAME="${DB_NAME:-terraos}"
    export DB_USER="${DB_USER:-terraos}"
    "$PYTHON" -m services.ingestion.bip_connector \
        --workers 10 \
        --max-sites 500 \
        --tenant-id "$TENANT_ID" \
        --db-dsn "$DB_DSN" \
        2>&1
) | while IFS= read -r line; do log "  [BIP] $line"; done
BIP_EXIT="${PIPESTATUS[0]}"

if [[ "$BIP_EXIT" -eq 0 ]]; then
    log "BIP connector: OK"
else
    log "BIP connector: FAILED (exit $BIP_EXIT) — continuing"
    FAILED=1
fi

# ── Stage 4: Geo enricher ────────────────────────────────────────────────────
log "--- Stage 4: Geo enricher (limit=10000) ---"
(
    cd "$BIP_DIR"
    export PYTHONPATH="$PYTHONPATH_INGEST"
    export DB_HOST="${DB_HOST:-127.0.0.1}"
    export DB_PORT="${DB_PORT:-5432}"
    export DB_NAME="${DB_NAME:-terraos}"
    export DB_USER="${DB_USER:-terraos}"
    "$PYTHON" geo_enricher.py --limit 10000 2>&1
) | while IFS= read -r line; do log "  [GEO] $line"; done
GEO_EXIT="${PIPESTATUS[0]}"

if [[ "$GEO_EXIT" -eq 0 ]]; then
    log "Geo enricher: OK"
else
    log "Geo enricher: FAILED (exit $GEO_EXIT)"
    FAILED=1
fi

# ── Summary ──────────────────────────────────────────────────────────────────
log "========================================================"
if [[ "$FAILED" -eq 0 ]]; then
    log "daily_ingest.sh DONE — all stages succeeded"
else
    log "daily_ingest.sh DONE — one or more stages FAILED (exit 1)"
fi
log "========================================================"

exit "$FAILED"
