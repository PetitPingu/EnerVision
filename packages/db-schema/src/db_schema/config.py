"""Configuration de connexion à la base PostgreSQL/TimescaleDB.

Package partagé : ne dépend d'aucune app en particulier — core_api et
etl_worker (ou tout autre service) peuvent s'y brancher indépendamment.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Paramètres de connexion à la base."""

    # Driver psycopg (v3) : même schéma d'URL (postgresql+psycopg://) pour un
    # moteur async (create_async_engine) ou sync (create_engine), pour qu'un
    # service synchrone puisse réutiliser DATABASE_URL sans dupliquer la
    # couche de connexion ni installer un autre driver.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://enervision:enervision@localhost:5432/enervision"
    )
