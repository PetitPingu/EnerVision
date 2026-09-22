"""Écrit chaque prédiction unitaire dans predictions_log (voir docs/monitoring_model.md).

Une ligne par appel à /predict, sans déduplication : sert de base au job
de rapprochement de l'ETL worker (MAE glissante 24h par site).
"""

import uuid
from datetime import datetime

from db_schema.models import PredictionLog
from sqlalchemy import create_engine

from .config import Config

_TABLE = PredictionLog.__table__


class PredictionLogWriter:
    """Insère une prédiction unitaire dans Postgres."""

    def __init__(self, engine=None):
        self._engine = engine or create_engine(Config.DATABASE_URL)

    def log(
        self,
        site_id: str,
        target_timestamp: datetime,
        predicted_consumption_kwh: float,
        model_version: str | None,
    ) -> None:
        stmt = _TABLE.insert().values(
            id=uuid.uuid4(),
            site_id=site_id,
            target_timestamp=target_timestamp,
            predicted_consumption_kwh=predicted_consumption_kwh,
            model_version=model_version,
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
