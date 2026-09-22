"""Composition : choisit l'implémentation concrète de TrainingDataPort /
StateTrainingDataPort."""

from application.ports import StateTrainingDataPort, TrainingDataPort
from infrastructure.config import Config
from infrastructure.training_data.consumption.json_file_reader import JsonFileTrainingDataReader
from infrastructure.training_data.consumption.mock_reader import MockTrainingDataReader
from infrastructure.training_data.consumption.postgres_reader import PostgresTrainingDataReader
from infrastructure.training_data.state.mock_reader import MockStateTrainingDataReader
from infrastructure.training_data.state.postgres_reader import (
    PostgresStateTrainingDataReader,
)


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


def create_state_training_data_reader() -> StateTrainingDataPort:
    """Instancie le lecteur d'état selon TRAINING_DATA_SOURCE (mock ou postgres -
    pas de source json, pas de cas d'usage local identifié pour l'instant)."""
    source = Config.TRAINING_DATA_SOURCE

    if source == "postgres":
        return PostgresStateTrainingDataReader(Config.DATABASE_URL)

    if source in ("mock", "json"):
        return MockStateTrainingDataReader()

    raise ValueError(f"TRAINING_DATA_SOURCE inconnu : {source}")
