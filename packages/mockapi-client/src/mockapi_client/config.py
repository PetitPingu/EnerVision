"""Configuration de connexion à l'API Mock EnerVision.

Rien n'est codé en dur : l'adresse et les identifiants de l'API mock
viennent des variables d'environnement (ENERVISION_API_HOST,
ENERVISION_API_PORT, ENERVISION_API_SCHEME, ENERVISION_API_USERNAME,
ENERVISION_API_PASSWORD, ENERVISION_REQUEST_TIMEOUT).
"""

import os

from dotenv import find_dotenv, load_dotenv

# usecwd=True : recherche le .env depuis le répertoire courant (celui de
# l'app appelante, ex. apps/etl_worker), pas depuis ce fichier — sinon la
# remontée d'arborescence s'arrête à packages/mockapi-client sans jamais
# atteindre le .env de l'app.
load_dotenv(find_dotenv(usecwd=True))


class Config:
    """Paramètres de connexion et de résilience de l'API Mock."""

    API_SCHEME = os.environ.get("ENERVISION_API_SCHEME", "http")
    API_HOST = os.environ.get("ENERVISION_API_HOST", "localhost")
    API_PORT = os.environ.get("ENERVISION_API_PORT", "8000")
    API_BASE_URL = f"{API_SCHEME}://{API_HOST}:{API_PORT}" if API_PORT else f"{API_SCHEME}://{API_HOST}"

    # Identifiants HTTP Basic Auth, si l'API mock en exige (facultatif).
    API_USERNAME = os.environ.get("ENERVISION_API_USERNAME") or None
    API_PASSWORD = os.environ.get("ENERVISION_API_PASSWORD") or None

    REQUEST_TIMEOUT = float(os.environ.get("ENERVISION_REQUEST_TIMEOUT", "5"))
    MAX_RETRIES = int(os.environ.get("ENERVISION_API_MAX_RETRIES", "3"))
    BACKOFF_BASE = float(os.environ.get("ENERVISION_API_BACKOFF_BASE", "0.5"))
