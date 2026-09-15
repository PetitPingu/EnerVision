"""Configuration de connexion à l'API Mock EnerVision.

Mêmes variables d'environnement que le reste du projet (ENERVISION_API_HOST,
ENERVISION_API_PORT, ENERVISION_REQUEST_TIMEOUT), pour ne pas coder en dur
l'adresse de l'API mock fournie par le formateur.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Paramètres de connexion et de résilience de l'API Mock."""

    API_HOST = os.environ.get("ENERVISION_API_HOST", "localhost")
    API_PORT = os.environ.get("ENERVISION_API_PORT", "8000")
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

    REQUEST_TIMEOUT = float(os.environ.get("ENERVISION_REQUEST_TIMEOUT", "5"))
    MAX_RETRIES = int(os.environ.get("ENERVISION_API_MAX_RETRIES", "3"))
    BACKOFF_BASE = float(os.environ.get("ENERVISION_API_BACKOFF_BASE", "0.5"))
