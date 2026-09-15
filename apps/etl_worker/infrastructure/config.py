"""Configuration du worker d'ingestion (issue #19).

Toutes les valeurs peuvent être surchargées par des variables
d'environnement (fichier .env), pour ne pas coder en dur les adresses des
services d'infrastructure.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Paramètres de connexion aux services d'infrastructure du worker."""

    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql://enervision:changeme@localhost:5432/enervision"
    )

    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ROOT_USER", "enervision")
    MINIO_SECRET_KEY = os.environ.get("MINIO_ROOT_PASSWORD", "changeme123")
    MINIO_BRONZE_BUCKET = os.environ.get("MINIO_BRONZE_BUCKET", "bronze")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    POLL_INTERVAL_SECONDS = int(os.environ.get("ETL_POLL_INTERVAL_SECONDS", "60"))
