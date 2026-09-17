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

    PREDICTION_URL = os.environ.get("PREDICTION_URL", "http://localhost:8002")
