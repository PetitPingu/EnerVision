"""Port (interface) que l'infrastructure doit implémenter.

L'application ne connaît que cette abstraction : elle ne dépend jamais de
SQLAlchemy, psycopg, MinIO ou de tout autre détail technique (inversion de
dépendance).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd
from sklearn.pipeline import Pipeline


class TrainingDataPort(ABC):
    """Accès aux lectures readings_curated pour l'entraînement ML."""

    @abstractmethod
    def fetch_training_data(self) -> pd.DataFrame:
        """Retourne les lectures prêtes pour features.build_features().

        Colonnes attendues : site_id, timestamp, consumption_kwh.
        Les lignes sans consumption_kwh sont exclues par l'implémentation.
        """


@dataclass(frozen=True)
class SavedModelMetadata:
    """Métadonnées d'un modèle persisté (accompagnent l'artifact joblib)."""

    model_name: str
    trained_at: str
    mae: float
    rmse: float
    train_size: int
    test_size: int
    features: tuple[str, ...]


class ModelStorePort(ABC):
    """Persistance des modèles entraînés (artifact + métadonnées)."""

    @abstractmethod
    def save(self, pipeline: Pipeline, metadata: SavedModelMetadata) -> str:
        """Enregistre le pipeline et retourne le préfixe de clé objet (version)."""

    @abstractmethod
    def load_latest(self, model_name: str) -> tuple[Pipeline, SavedModelMetadata]:
        """Charge le modèle pointé par {model_name}/latest/."""
