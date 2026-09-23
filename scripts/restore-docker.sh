#!/usr/bin/env bash
# Re-exécuter avec bash si lancé via sh (dash ne supporte pas pipefail)
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-$HOME/docker-backups}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

SKIP_CONFIRM=false
COMPOSE_DOWN=false
POSTGRES_SQL=false
SKIP_VOLUMES=false
WORK_DIR=""

usage() {
  cat <<'EOF'
Usage: restore-docker.sh <sauvegarde> [options]

  sauvegarde : répertoire YYYYMMDD-HHMMSS ou archive enervision-volumes-*.tar.gz

Options:
  --yes              Ne pas demander de confirmation
  --compose-down     Arrêter la stack avec docker compose down avant restauration
  --postgres-sql     Restaurer PostgreSQL via postgres_dump.sql (ignore le volume postgres-data)
  --skip-volumes     Ne pas restaurer les volumes (utile avec --postgres-sql seul)
  -h, --help         Afficher cette aide

Par défaut, tous les volumes sont restaurés depuis les archives .tar.gz.
Le dump SQL n'est pas rejoué automatiquement (redondant si postgres-data est restauré).
EOF
  exit "${1:-0}"
}

cleanup() {
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    rm -rf "$WORK_DIR"
  fi
}

confirm() {
  if $SKIP_CONFIRM; then
    return 0
  fi
  echo
  echo "ATTENTION : cette opération va écraser les données actuelles des volumes."
  read -r -p "Continuer ? [o/N] " reply
  case "$reply" in
    o|O|oui|Oui|OUI) return 0 ;;
    *) echo "Annulé."; exit 0 ;;
  esac
}

resolve_backup_dir() {
  local source="$1"

  if [[ -f "$source" && "$source" == *.tar.gz ]]; then
    WORK_DIR=$(mktemp -d)
    trap cleanup EXIT
    echo "→ Extraction de l'archive..."
    tar xzf "$source" -C "$WORK_DIR"
    BACKUP_DIR="$WORK_DIR"
  elif [[ -d "$source" ]]; then
    BACKUP_DIR="$source"
  else
    # Essayer dans BACKUP_ROOT (ex: 20250923-153000)
    if [[ -d "$BACKUP_ROOT/$source" ]]; then
      BACKUP_DIR="$BACKUP_ROOT/$source"
    else
      echo "Erreur : sauvegarde introuvable : $source"
      exit 1
    fi
  fi
}

stop_containers_using_volume() {
  local volume="$1"
  local containers

  containers=$(docker ps -q --filter "volume=$volume" || true)
  if [[ -n "$containers" ]]; then
    echo "  → Arrêt des conteneurs utilisant $volume..."
    # shellcheck disable=SC2086
    docker stop $containers >/dev/null
  fi
}

restore_volume() {
  local archive="$1"
  local volume
  local base

  base=$(basename "$archive" .tar.gz)
  volume="$base"

  if $POSTGRES_SQL && [[ "$volume" == *postgres-data* ]]; then
    echo "→ Volume ignoré (mode --postgres-sql) : $volume"
    return 0
  fi

  echo "→ Restauration du volume : $volume"
  stop_containers_using_volume "$volume"

  if ! docker volume inspect "$volume" >/dev/null 2>&1; then
    echo "  → Création du volume $volume"
    docker volume create "$volume" >/dev/null
  fi

  docker run --rm \
    -v "${volume}":/volume \
    -v "$BACKUP_DIR":/backup:ro \
    alpine:3.20 \
    sh -c 'find /volume -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar xzf "/backup/'"$base"'.tar.gz" -C /volume'
}

restore_postgres_sql() {
  local dump="$BACKUP_DIR/postgres_dump.sql"

  if [[ ! -f "$dump" ]]; then
    echo "Aucun postgres_dump.sql dans la sauvegarde."
    return 0
  fi

  if ! docker ps --format '{{.Names}}' | grep -qx postgres; then
    echo "Erreur : le conteneur postgres doit être démarré pour restaurer le dump SQL."
    echo "Lancez d'abord : docker compose up -d postgres"
    exit 1
  fi

  echo "→ Restauration PostgreSQL via dump SQL..."
  echo "  (le volume postgres-data doit être vide ou supprimé au préalable)"
  docker exec -i postgres psql -U "$POSTGRES_USER" -v ON_ERROR_STOP=1 < "$dump"
}

# --- Arguments ---
if [[ $# -lt 1 ]]; then
  usage 1
fi

BACKUP_SOURCE="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) SKIP_CONFIRM=true ;;
    --compose-down) COMPOSE_DOWN=true ;;
    --postgres-sql) POSTGRES_SQL=true ;;
    --skip-volumes) SKIP_VOLUMES=true ;;
    -h|--help) usage 0 ;;
    *)
      echo "Option inconnue : $1"
      usage 1
      ;;
  esac
  shift
done

resolve_backup_dir "$BACKUP_SOURCE"
echo "Restauration depuis : $BACKUP_DIR"
confirm

if $COMPOSE_DOWN; then
  if [[ -f "$COMPOSE_FILE" ]]; then
    echo "→ docker compose down..."
    docker compose -f "$COMPOSE_FILE" down
  else
    echo "Avertissement : $COMPOSE_FILE introuvable, --compose-down ignoré."
  fi
fi

if ! $SKIP_VOLUMES; then
  shopt -s nullglob
  archives=("$BACKUP_DIR"/*.tar.gz)
  shopt -u nullglob

  if [[ ${#archives[@]} -eq 0 ]]; then
    echo "Aucune archive de volume (.tar.gz) trouvée."
  else
    for archive in "${archives[@]}"; do
      restore_volume "$archive"
    done
  fi
fi

if $POSTGRES_SQL; then
  restore_postgres_sql
elif [[ -f "$BACKUP_DIR/postgres_dump.sql" ]]; then
  echo
  echo "Note : postgres_dump.sql présent mais non restauré (utilisez --postgres-sql si besoin)."
fi

echo
echo "Terminé. Redémarrez la stack si nécessaire : docker compose up -d"
