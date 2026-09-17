FROM python:3.12-slim

WORKDIR /app

# Contexte de build = racine du repo (voir docker-compose.yml), pour copier
# packages/ (dépendance partagée db-schema) dans l'image.
COPY packages/ /packages/
COPY apps/prediction/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/prediction/ .

EXPOSE 8000

CMD ["uvicorn", "presentation.api:app", "--host", "0.0.0.0", "--port", "8000"]
