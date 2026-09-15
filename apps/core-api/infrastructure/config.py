"""Configuration de connexion à l'API mock EnerVision.

Toutes les valeurs peuvent être surchargées par des variables d'environnement
(fichier .env), pour ne pas coder en dur l'adresse de l'API mock (fournie
par le formateur).
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Paramètres de connexion à l'API mock."""

    API_HOST = os.environ.get("ENERVISION_API_HOST", "localhost")
    API_PORT = os.environ.get("ENERVISION_API_PORT", "8000")
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

    REQUEST_TIMEOUT = float(os.environ.get("ENERVISION_REQUEST_TIMEOUT", "5"))
