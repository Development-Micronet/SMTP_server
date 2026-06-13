#!/usr/bin/env bash
# Nightly backup: SQL dump + Maildir snapshot via restic.
# Requires RESTIC_REPOSITORY and RESTIC_PASSWORD in the environment.
set -euo pipefail
STAMP=$(date +%F)
TMP=$(mktemp -d)

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-mailstack}" \
  "${POSTGRES_DB:-mailstack}" > "$TMP/mailstack-$STAMP.sql"

VMAIL_VOL=$(docker volume inspect -f '{{.Mountpoint}}' "$(basename "$PWD")_vmail")

restic backup "$TMP" "$VMAIL_VOL" --tag mailstack
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
rm -rf "$TMP"
echo "Backup $STAMP complete."
