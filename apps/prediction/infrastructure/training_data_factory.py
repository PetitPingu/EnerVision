"""Composition : choisit l'implémentation concrète de TrainingDataPort."""

from application.ports import TrainingDataPort
from infrastructure.config import Config
from infrastructure.json_file_training_data_reader import JsonFileTrainingDataReader
from infrastructure.mock_training_data_reader import MockTrainingDataReader


def create_training_data_reader() -> TrainingDataPort:
    """Instancie le lecteur selon TRAINING_DATA_SOURCE (mock ou json)."""
    if Config.TRAINING_DATA_SOURCE == "json":
        if not Config.TRAINING_DATA_JSON_PATH:
            raise ValueError(
                "TRAINING_DATA_JSON_PATH est requis quand TRAINING_DATA_SOURCE=json"
            )
        return JsonFileTrainingDataReader(Config.TRAINING_DATA_JSON_PATH)

    return MockTrainingDataReader()
