FROM python:3.12-slim

WORKDIR /app

# Contexte de build = racine du repo (voir docker-compose.yml), pour copier
# packages/ (dépendance partagée db-schema) dans l'image.
COPY packages/ /packages/
COPY apps/recommendation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/recommendation/ .

EXPOSE 8000

# Applique les migrations Alembic avant de démarrer, pour que le schéma
# existe dès le premier `docker compose up`. Le schéma vit dans
# packages/db-schema (partagé avec core_api), idempotent si déjà appliqué.
CMD ["sh", "-c", "alembic -c /packages/db-schema/alembic.ini upgrade head && uvicorn presentation.api:app --host 0.0.0.0 --port 8000"]
