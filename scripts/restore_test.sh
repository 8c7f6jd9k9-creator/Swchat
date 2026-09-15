#!/bin/sh
set -eu
: "${BACKUP_FILE:?Set BACKUP_FILE}"
: "${RESTORE_DATABASE_URL:?Set RESTORE_DATABASE_URL to disposable staging DB}"
pg_restore --clean --if-exists --no-owner -d "$RESTORE_DATABASE_URL" "$BACKUP_FILE"
psql "$RESTORE_DATABASE_URL" -c "SELECT count(*) AS users FROM users;"
psql "$RESTORE_DATABASE_URL" -c "SELECT count(*) AS audit_rows FROM audit_log;"
echo "Restore smoke test completed."
