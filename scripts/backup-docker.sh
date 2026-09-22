#!/usr/bin/env bash
# Re-exécuter avec bash si lancé via sh (dash ne supporte pas pipefail)
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-$HOME/docker-backups}"
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$STAMP"
mkdir -p "$BACKUP_DIR"

echo "Sauvegarde dans : $BACKUP_DIR"

# 1) Dump PostgreSQL (plus fiable qu'un tar brut pour la BDD)
if docker ps --format '{{.Names}}' | grep -qx postgres; then
  echo "→ Dump PostgreSQL..."
  docker exec postgres pg_dumpall -U "${POSTGRES_USER:-postgres}" \
    > "$BACKUP_DIR/postgres_dump.sql"
fi

# 2) Sauvegarde de tous les volumes Docker en tar.gz
for volume in $(docker volume ls -q); do
  echo "→ Volume : $volume"
  docker run --rm \
    -v "${volume}":/volume:ro \
    -v "$BACKUP_DIR":/backup \
    alpine:3.20 \
    tar czf "/backup/${volume}.tar.gz" -C /volume .
done

# 3) Archive globale (optionnel, pratique pour copier ailleurs)
tar czf "$BACKUP_ROOT/enervision-volumes-$STAMP.tar.gz" -C "$BACKUP_DIR" .
echo "Terminé : $BACKUP_ROOT/enervision-volumes-$STAMP.tar.gz"
