FROM python:3.12-slim

WORKDIR /app

# Contexte de build = racine du repo (voir docker-compose.yml), pour copier
# packages/ (dépendance partagée db-schema) dans l'image.
COPY packages/ /packages/
COPY apps/prediction/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/prediction/ .

EXPOSE 8000

# main.py (pas uvicorn directement) : câble le scheduler APScheduler
# (ré-entraînement 24h des 2 modèles) et le check de démarrage
# ("Modèle Production chargé au démarrage") avant de servir l'API.
CMD ["python", "main.py"]
