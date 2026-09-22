"""Configuration de connexion à la base PostgreSQL/TimescaleDB.

Package partagé : ne dépend d'aucune app en particulier — core_api et
etl_worker (ou tout autre service) peuvent s'y brancher indépendamment.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Paramètres de connexion à la base."""

    # +psycopg (v3) fonctionne pour un moteur async (create_async_engine)
    # comme sync (create_engine) — un service synchrone peut donc
    # réutiliser cette même DATABASE_URL sans installer un autre driver.
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://enervision:enervision@localhost:5432/enervision"
    )
