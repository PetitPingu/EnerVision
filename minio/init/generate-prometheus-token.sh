#!/bin/bash
set -e

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null

out=$(mc admin prometheus generate local)
token=""
while IFS= read -r line; do
  case "$line" in
    *bearer_token:*) token="${line#*bearer_token: }" ;;
  esac
done <<< "$out"

if [ -z "$token" ]; then
  echo "Impossible d'extraire le bearer_token depuis 'mc admin prometheus generate'" >&2
  exit 1
fi

printf '%s' "$token" > /secrets/minio-token
echo "Token Prometheus MinIO généré dans /secrets/minio-token"
