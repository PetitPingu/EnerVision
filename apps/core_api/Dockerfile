FROM python:3.12-slim

WORKDIR /app

# Contexte de build = racine du repo (voir docker-compose.yml), pour copier
# packages/ (dépendance partagée mockapi-client) dans l'image.
COPY packages/ /packages/
COPY apps/core_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/core_api/ .

EXPOSE 8000

CMD ["uvicorn", "presentation.api:app", "--host", "0.0.0.0", "--port", "8000"]
