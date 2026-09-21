"""Lecteur mock des données d'entraînement (en attendant Postgres).

Simule le résultat d'une requête SQL sur readings_curated
(colonnes site_id / timestamp / consumption_kwh).
"""

import pandas as pd

from application.ports import TrainingDataPort
from infrastructure.ml.consumption.features import RAW_COLUMNS


class MockTrainingDataReader(TrainingDataPort):
    """Retourne des lectures synthétiques pour développer sans base de données."""

    def fetch_training_data(self) -> pd.DataFrame:
        rows = []
        for i in range(40):
            site_num = (i % 7) + 1
            hour = 8 + (i % 12)
            minute = (i * 7) % 60
            rows.append(
                {
                    "site_id": f"SITE00{site_num}",
                    "timestamp": f"2026-09-07T{hour:02d}:{minute:02d}:00",
                    "consumption_kwh": 100.0 + site_num * 80 + hour * 5 + (i % 3) * 10,
                }
            )
        return pd.DataFrame(rows, columns=RAW_COLUMNS)
