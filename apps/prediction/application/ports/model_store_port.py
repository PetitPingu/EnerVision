"""Port de persistance des modèles entraînés."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class SavedModelMetadata:
    """Métadonnées d'un modèle persisté (accompagnent l'artifact joblib).

    `metrics` est un dict générique (ex. {"mae": .., "rmse": ..} pour un
    modèle de régression, {"accuracy": .., "f1_macro": ..} pour un modèle
    de classification) : ModelStorePort et ses implémentations ne
    connaissent aucun nom de métrique en particulier, ce qui leur permet de
    servir n'importe quel modèle (voir predict_state.py pour un second
    modèle - classification - qui réutilise cette même abstraction).
    """

    model_name: str
    trained_at: str
    metrics: dict[str, float]
    train_size: int
    test_size: int
    features: tuple[str, ...]

    @property
    def mae(self) -> float:
        return self.metrics["mae"]

    @property
    def rmse(self) -> float:
        return self.metrics["rmse"]


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
