#!/bin/bash
# Faza 65/111 — Automated PostgreSQL backup with retention + syslog
# Cron: 0 2 * * * /home/ubuntu/terra-os/scripts/backup.sh

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/terraos
RETENTION_DAYS=30
BACKUP_FILE="${BACKUP_DIR}/terraos_${DATE}.sql.gz"

# Log helper: writes to both stdout and syslog
log() {
    local msg="[terraos-backup] $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg"
    logger -t terraos-backup "$msg" || true
}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log "Starting backup → ${BACKUP_FILE}"

# Run pg_dump; exit non-zero on failure
if sudo -u postgres pg_dump terraos | gzip > "${BACKUP_FILE}"; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log "Backup completed: ${BACKUP_FILE} (${SIZE})"
else
    log "ERROR: pg_dump failed for database 'terraos'"
    logger -t terraos-backup -p user.err "CRITICAL: pg_dump failed — backup NOT created"
    exit 1
fi

# Retention: remove backups older than RETENTION_DAYS days
DELETED=$(find "$BACKUP_DIR" -name '*.sql.gz' -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "Retention cleanup: removed ${DELETED} backup(s) older than ${RETENTION_DAYS} days"
fi

log "Done. Current backups in ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || log "  (no backups found)"

exit 0
