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
        "DATABASE_URL", "postgresql://enervision:changeme@localhost:5432/enervision"
    )
    PORT = int(os.environ.get("PREDICTION_PORT", "8000"))

    # mock : données synthétiques | json : fichier local | postgres : après rebase dev
    TRAINING_DATA_SOURCE = os.environ.get("TRAINING_DATA_SOURCE", "mock")
    TRAINING_DATA_JSON_PATH = os.environ.get("TRAINING_DATA_JSON_PATH", "")
