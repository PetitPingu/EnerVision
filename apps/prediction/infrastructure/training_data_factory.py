"""Composition : choisit l'implémentation concrète de TrainingDataPort."""

from application.ports import TrainingDataPort
from infrastructure.config import Config
from infrastructure.json_file_training_data_reader import JsonFileTrainingDataReader
from infrastructure.mock_training_data_reader import MockTrainingDataReader
from infrastructure.postgres_training_data_reader import PostgresTrainingDataReader


def create_training_data_reader() -> TrainingDataPort:
    """Instancie le lecteur selon TRAINING_DATA_SOURCE (mock, json ou postgres)."""
    source = Config.TRAINING_DATA_SOURCE

    if source == "postgres":
        return PostgresTrainingDataReader(Config.DATABASE_URL)

    if source == "json":
        if not Config.TRAINING_DATA_JSON_PATH:
            raise ValueError(
                "TRAINING_DATA_JSON_PATH est requis quand TRAINING_DATA_SOURCE=json"
            )
        return JsonFileTrainingDataReader(Config.TRAINING_DATA_JSON_PATH)

    if source == "mock":
        return MockTrainingDataReader()

    raise ValueError(f"TRAINING_DATA_SOURCE inconnu : {source}")
