#!/bin/bash
# SQLite database backup script for API Pilot
# Usage: ./scripts/backup_db.sh [backup_dir]

set -euo pipefail

BACKUP_DIR="${1:-./backups}"
DB_PATH="./data/api_pilot.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/api_pilot_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    exit 1
fi

# Use SQLite .backup command for consistent backup (works while DB is in use)
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/api_pilot_*.db 2>/dev/null | tail -n +8 | xargs -r rm -f

# Compress older backups
for f in "$BACKUP_DIR"/api_pilot_*.db; do
    if [ "$(basename "$f")" != "$(basename "$BACKUP_FILE")" ] && [ ! -f "${f}.gz" ]; then
        gzip "$f"
    fi
done

echo "Backup created: $BACKUP_FILE"
