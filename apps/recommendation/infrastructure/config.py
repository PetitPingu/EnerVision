"""Configuration du service Recommandation.

DATABASE_URL vit dans le package partagé db_schema (packages/db-schema) ;
seule l'adresse du service Prediction, propre à ce service, est définie ici
(voir docs/seq_predict_call.md, "Appel au Service Recommandation").
"""

import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


class Config:
    """Paramètres de connexion au service Prediction."""

    PREDICTION_URL = os.environ.get("PREDICTION_URL", "http://localhost:8002")
    REQUEST_TIMEOUT = float(os.environ.get("RECOMMENDATION_REQUEST_TIMEOUT", "5"))
