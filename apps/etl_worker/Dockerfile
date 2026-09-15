FROM python:3.12-slim

WORKDIR /app

# Contexte de build = racine du repo (voir docker-compose.yml), pour copier
# packages/ (dépendance partagée mockapi-client) dans l'image.
COPY packages/ /packages/
COPY apps/etl_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/etl_worker/ .

CMD ["python", "main.py"]
