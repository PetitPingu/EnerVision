"""Lit les données d'entraînement du modèle d'état depuis readings_curated
(Postgres).

Même stack que PostgresTrainingDataReader (régression), colonne cible
différente : data_quality au lieu de consumption_kwh, et pas de filtre
consumption_kwh IS NOT NULL - une lecture critical (donc sans mesure) est
justement un exemple d'entraînement valide pour ce modèle.
"""

import pandas as pd
from db_schema.models import ReadingCurated
from sqlalchemy import create_engine, select

from application.ports import StateTrainingDataPort
from infrastructure.ml.state.features import RAW_COLUMNS, SENSOR_COLUMNS


class PostgresStateTrainingDataReader(StateTrainingDataPort):
    """Charge les lectures curées prêtes pour state_features.build_features()."""

    def __init__(self, database_url: str, engine=None):
        self._engine = engine or create_engine(database_url)

    def fetch_training_data(self) -> pd.DataFrame:
        stmt = (
            select(
                ReadingCurated.site_id,
                ReadingCurated.timestamp,
                ReadingCurated.data_quality,
                *(getattr(ReadingCurated, name) for name in SENSOR_COLUMNS),
            )
            .where(ReadingCurated.data_quality.is_not(None))
            .order_by(ReadingCurated.timestamp)
        )
        df = pd.read_sql(stmt, self._engine)
        return df[RAW_COLUMNS]
