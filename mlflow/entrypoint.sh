#!/bin/sh
set -e

export PGPASSWORD="$POSTGRES_PASSWORD"
until psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" >/dev/null 2>&1; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

# Schéma Postgres dédié à MLflow (voir docs/archi_infra.md : "backend store
# de MLflow ... dans un schéma dédié - pas de base supplémentaire à
# opérer"), créé ici car MLflow ne crée que ses tables, pas le schéma.
psql -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "CREATE SCHEMA IF NOT EXISTS ${MLFLOW_DB_SCHEMA:-mlflow};"

# Force l'addressing style "path" (bucket.minio:9000 ne résout pas en DNS),
# requis pour que boto3 parle correctement à MinIO.
mkdir -p "$HOME/.aws"
cat > "$HOME/.aws/config" <<EOF
[default]
s3 =
    addressing_style = path
EOF

BACKEND_STORE_URI="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?options=-csearch_path%3D${MLFLOW_DB_SCHEMA:-mlflow}"

# Protection anti DNS-rebinding de MLflow 3.x (CVE-2025-14279) : rejette par
# défaut tout Host qui n'est pas localhost/IP privée - "mlflow" (le nom DNS
# interne Docker utilisé par les autres conteneurs du réseau) doit être
# explicitement autorisé, sinon 403 "Invalid Host header" sur chaque appel.
exec mlflow server \
  --backend-store-uri "$BACKEND_STORE_URI" \
  --default-artifact-root "s3://${MINIO_MODELS_BUCKET:-models}/" \
  --host 0.0.0.0 \
  --port 5000 \
  --allowed-hosts "mlflow,mlflow:5000,localhost,localhost:5000,127.0.0.1,127.0.0.1:5000"