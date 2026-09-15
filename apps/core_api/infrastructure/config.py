"""Configuration de connexion à l'API mock EnerVision.

Toutes les valeurs peuvent être surchargées par des variables d'environnement
(fichier .env), pour ne pas coder en dur l'adresse de l'API mock (fournie
par le formateur).
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Paramètres de connexion à l'API mock et à la base PostgreSQL/TimescaleDB."""

    API_HOST = os.environ.get("ENERVISION_API_HOST", "localhost")
    API_PORT = os.environ.get("ENERVISION_API_PORT", "8000")
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

    REQUEST_TIMEOUT = float(os.environ.get("ENERVISION_REQUEST_TIMEOUT", "5"))

    # Driver psycopg (v3) : même schéma d'URL (postgresql+psycopg://) pour un
    # moteur async (create_async_engine, utilisé ici) ou sync (create_engine),
    # pour qu'un futur service synchrone puisse réutiliser DATABASE_URL sans
    # dupliquer la couche de connexion ni installer un autre driver.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://enervision:enervision@localhost:5432/enervision"
    )
