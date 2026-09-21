"""Use case : ré-entraîne le modèle d'état et ne le promeut que s'il est
meilleur.

Même pattern champion/challenger que retrain_if_better (régression
consommation), avec une différence : la métrique de comparaison est
l'accuracy, où plus haut est meilleur (contrairement au MAE, à minimiser).
"""

from dataclasses import dataclass

from application.ports import ModelStorePort, SavedModelMetadata, StateTrainingDataPort
from infrastructure.ml.state.features import FEATURE_COLUMNS
from infrastructure.ml.state.trainer import StateTrainingResult, train_model
from infrastructure.model_store import utc_version_timestamp


@dataclass(frozen=True)
class StateRetrainResult:
    """Résultat d'un cycle de ré-entraînement planifié du modèle d'état."""

    training: StateTrainingResult
    metadata: SavedModelMetadata
    promoted: bool
    champion_accuracy: float | None


def retrain_state_if_better(
    data_reader: StateTrainingDataPort,
    model_store: ModelStorePort,
    model_name: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> StateRetrainResult:
    """Entraîne un candidat et ne le promeut que s'il bat le champion actuel
    (accuracy la plus haute)."""
    df = data_reader.fetch_training_data()
    if df.empty:
        raise ValueError("Aucune donnee d'entrainement disponible")

    training = train_model(df, test_size=test_size, random_state=random_state)
    metadata = SavedModelMetadata(
        model_name=model_name,
        trained_at=utc_version_timestamp(),
        metrics={"accuracy": training.accuracy, "f1_macro": training.f1_macro},
        train_size=training.train_size,
        test_size=training.test_size,
        features=tuple(FEATURE_COLUMNS),
    )

    champion = model_store.get_current_metadata(model_name)
    version = model_store.register(training.pipeline, metadata)

    champion_accuracy = champion.metrics["accuracy"] if champion is not None else None
    promoted = champion_accuracy is None or metadata.metrics["accuracy"] > champion_accuracy
    if promoted:
        model_store.promote(model_name, version)

    return StateRetrainResult(
        training=training,
        metadata=metadata,
        promoted=promoted,
        champion_accuracy=champion_accuracy,
    )
