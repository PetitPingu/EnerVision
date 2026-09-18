"""Configuration de connexion à l'API mock EnerVision.

Toutes les valeurs peuvent être surchargées par des variables d'environnement
(fichier .env), pour ne pas coder en dur l'adresse de l'API mock (fournie
par le formateur). La configuration DB (DATABASE_URL) vit dans le package
partagé db_schema (packages/db-schema), pas ici.
"""

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


class Config:
    """Paramètres de connexion à l'API mock."""

    API_SCHEME = os.environ.get("ENERVISION_API_SCHEME", "http")
    API_HOST = os.environ.get("ENERVISION_API_HOST", "localhost")
    API_PORT = os.environ.get("ENERVISION_API_PORT", "8000")
    API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}" if API_PORT else f"{API_SCHEME}://{API_HOST}"

    REQUEST_TIMEOUT = float(os.environ.get("ENERVISION_REQUEST_TIMEOUT", "5"))

    # Redis Streams (alert.detected, publié par etl_worker) : REDIS_HOST vaut
    # "redis" sous docker-compose (nom du service), "localhost" en dev hors
    # compose.
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
    ALERT_STREAM_BLOCK_MS = int(os.environ.get("ALERT_STREAM_BLOCK_MS", "15000"))

    PREDICTION_URL = os.environ.get("PREDICTION_URL", "http://localhost:8002")
    RECOMMENDATION_URL = os.environ.get("RECOMMENDATION_URL", "http://localhost:8003")

    # JWT (voir docs/seq_auth_token.md). Le défaut n'est valable qu'en dev :
    # tout déploiement réel doit fournir JWT_SECRET_KEY explicitement.
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "dev-insecure-secret-change-me-in-production-32chars"
    )
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "30"))
