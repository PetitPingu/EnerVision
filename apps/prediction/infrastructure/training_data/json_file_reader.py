"""Lecteur des données d'entraînement depuis un fichier JSON local.

Utile en développement local (ex. tests/test.json) sans connexion Postgres.
"""

import json
from pathlib import Path

import pandas as pd

from application.ports import TrainingDataPort
from infrastructure.ml.features import RAW_COLUMNS


class JsonFileTrainingDataReader(TrainingDataPort):
    """Charge un export JSON de lectures et applique le filtre data_quality='good'."""

    def __init__(self, path: Path | str):
        self._path = Path(path)

    def fetch_training_data(self) -> pd.DataFrame:
        with self._path.open(encoding="utf-8") as f:
            readings = json.load(f)

        raw_df = pd.DataFrame(readings)
        return raw_df.loc[raw_df["data_quality"] == "good", RAW_COLUMNS].reset_index(drop=True)
