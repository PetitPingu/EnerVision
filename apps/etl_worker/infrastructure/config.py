"""Configuration du worker d'ingestion.

Toutes les valeurs peuvent être surchargées par des variables
d'environnement (fichier .env), pour ne pas coder en dur les adresses des
services d'infrastructure.
"""

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


class Config:
    """Paramètres de connexion aux services d'infrastructure du worker."""

    # Utilisée par CuratedWriter pour écrire dans readings_curated.
    # +psycopg est nécessaire : c'est le driver (v3) partagé avec
    # db-schema, pas l'ancien psycopg2.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://enervision:changeme@localhost:5432/enervision"
    )

    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ROOT_USER", "enervision")
    MINIO_SECRET_KEY = os.environ.get("MINIO_ROOT_PASSWORD", "changeme123")
    MINIO_RAW_BUCKET = os.environ.get("MINIO_RAW_BUCKET", "raw")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"

    POLL_INTERVAL_SECONDS = int(os.environ.get("ETL_POLL_INTERVAL_SECONDS", "60"))

    # Redis Streams (alert.detected) : REDIS_HOST vaut "redis" sous
    # docker-compose (nom du service), "localhost" en dev hors compose.
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

    # Monitoring du modèle (docs/monitoring_model.md) : rapprochement MAE
    # 24h + drift, moins fréquent que le job ETL principal.
    MODEL_HEALTH_INTERVAL_SECONDS = int(
        os.environ.get("MODEL_HEALTH_INTERVAL_SECONDS", str(60 * 60))
    )
    # Fenêtre (en jours) avant metadata.trained_at utilisée comme référence
    # "entraînement" pour le calcul de drift - cohérent avec l'historique
    # court (~10 jours) mentionné dans features.py côté apps/prediction.
    TRAINING_WINDOW_DAYS = int(os.environ.get("TRAINING_WINDOW_DAYS", "10"))
    METRICS_PORT = int(os.environ.get("ETL_METRICS_PORT", "9200"))
    # Historique regardé pour construire le profil d'erreur par horizon
    # (domain/model_health.py:compute_mae_by_horizon, tranches jusqu'à 7j) :
    # plus large que TRAINING_WINDOW_DAYS pour avoir assez de prédictions
    # rapprochées sur les tranches d'horizon longues.
    HORIZON_PROFILE_LOOKBACK_DAYS = int(os.environ.get("HORIZON_PROFILE_LOOKBACK_DAYS", "30"))
