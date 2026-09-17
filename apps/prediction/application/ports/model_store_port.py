"""Port de persistance des modèles entraînés."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sklearn.pipeline import Pipeline


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
        """Charge le dernier modèle entraîné pour {model_name} (implémentation-
        dépendant : pointeur {model_name}/latest/ pour MinioModelStore, alias
        de Model Registry pour MlflowModelStore)."""

    @abstractmethod
    def register(self, pipeline: Pipeline, metadata: SavedModelMetadata) -> str:
        """Enregistre une nouvelle version sans la mettre en production.

        Utilisé par le ré-entraînement planifié (champion/challenger) : le
        candidat doit être conservé (historique, comparaison a posteriori)
        même s'il n'est pas meilleur que le modèle actuellement servi. Voir
        promote(). Retourne l'identifiant de version à passer à promote().
        """

    @abstractmethod
    def promote(self, model_name: str, version: str) -> None:
        """Fait de {version} le modèle servi par load_latest() pour {model_name}."""

    @abstractmethod
    def get_current_metadata(self, model_name: str) -> SavedModelMetadata | None:
        """Métadonnées du modèle actuellement en production, ou None si
        {model_name} n'a encore jamais été promu."""
