"""Configuration du service Prediction.

Toutes les valeurs peuvent être surchargées par des variables
d'environnement (fichier .env), pour ne pas coder en dur les adresses des
services d'infrastructure.
"""

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


class Config:
    """Paramètres de connexion et d'exécution du service Prediction."""

    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://enervision:changeme@localhost:5432/enervision",
    )
    PORT = int(os.environ.get("PREDICTION_PORT", "8000"))

    # mock : données synthétiques | json : fichier local | postgres : readings_curated
    TRAINING_DATA_SOURCE = os.environ.get("TRAINING_DATA_SOURCE", "mock")
    TRAINING_DATA_JSON_PATH = os.environ.get("TRAINING_DATA_JSON_PATH", "")

    # MinIO — mêmes variables d'environnement que l'ETL (voir .env racine).
    MODEL_STORE = os.environ.get("MODEL_STORE", "minio")
    MODEL_NAME = os.environ.get("MODEL_NAME", "energy-consumption")
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ROOT_USER", "enervision")
    MINIO_SECRET_KEY = os.environ.get("MINIO_ROOT_PASSWORD", "changeme123")
    MINIO_MODELS_BUCKET = os.environ.get("MINIO_MODELS_BUCKET", "models")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
