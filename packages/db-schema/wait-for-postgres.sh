#!/bin/sh
# Attend que PostgreSQL accepte les connexions (variable DATABASE_URL requise).
set -e

if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is not set" >&2
  exit 1
fi

until python - <<'PY'
import os
import sys

import psycopg

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
try:
    with psycopg.connect(url):
        pass
except Exception:
    sys.exit(1)
PY
do
  echo "Waiting for PostgreSQL..."
  sleep 2
done
