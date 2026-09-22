FROM python:3.12-slim

WORKDIR /app

# Contexte de build = racine du repo (voir docker-compose.yml), pour copier
# packages/ (dépendances partagées mockapi-client, db-schema) dans l'image.
COPY packages/ /packages/
COPY apps/core_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/core_api/ .

EXPOSE 8000

# Applique les migrations Alembic (tables + hypertable TimescaleDB) avant de
# démarrer, pour que le schéma existe dès le premier `docker compose up`.
# Le schéma vit dans packages/db-schema (partagé, pas propre à core_api) :
# n'importe quel autre service peut appliquer ces migrations de la même
# façon, sans dépendre du démarrage de core_api.
CMD ["sh", "-c", "sh /packages/db-schema/wait-for-postgres.sh && alembic -c /packages/db-schema/alembic.ini upgrade head && uvicorn presentation.api:app --host 0.0.0.0 --port 8000"]
