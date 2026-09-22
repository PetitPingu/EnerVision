FROM python:3.12-slim

# postgresql-client fournit psql, utilisé par entrypoint.sh pour créer le
# schéma dédié avant de démarrer le serveur MLflow (voir docs/archi_infra.md).
# curl : utilisé par le healthcheck docker-compose (GET /health).
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY mlflow/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mlflow/entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
