#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
mkdir -p "$BACKUP_DIR"

STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$BACKUP_DIR/noticias-${STAMP}.dump"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-noticias}" -F c "${POSTGRES_DB:-noticias}" > "$OUT"
echo "Backup saved: $OUT"

# Rotate
find "$BACKUP_DIR" -name "noticias-*.dump" -type f -mtime "+${RETAIN_DAYS}" -delete
echo "Rotated backups older than ${RETAIN_DAYS} days."
