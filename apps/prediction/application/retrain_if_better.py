"""Use case : ré-entraîne le modèle et ne le promeut que s'il est meilleur.

Pattern champion/challenger : le candidat ("challenger") est toujours
enregistré (historique, traçabilité), mais ne remplace le modèle servi
("champion", metadata.mae le plus bas via model_store.get_current_metadata())
que s'il fait strictement mieux. Sans champion existant (premier
entraînement), le challenger est promu d'office.
"""

from dataclasses import dataclass

from application.ports import ModelStorePort, SavedModelMetadata, TrainingDataPort
from infrastructure.model_store import utc_version_timestamp
from infrastructure.ml.features import FEATURE_COLUMNS
from infrastructure.ml.trainer import TrainingResult, train_model


@dataclass(frozen=True)
class RetrainResult:
    """Résultat d'un cycle de ré-entraînement planifié."""

    training: TrainingResult
    metadata: SavedModelMetadata
    promoted: bool
    champion_mae: float | None


def retrain_if_better(
    data_reader: TrainingDataPort,
    model_store: ModelStorePort,
    model_name: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> RetrainResult:
    """Entraîne un candidat et ne le promeut que s'il bat le champion actuel."""
    df = data_reader.fetch_training_data()
    if df.empty:
        raise ValueError("Aucune donnee d'entrainement disponible")

    training = train_model(df, test_size=test_size, random_state=random_state)
    metadata = SavedModelMetadata(
        model_name=model_name,
        trained_at=utc_version_timestamp(),
        mae=training.mae,
        rmse=training.rmse,
        train_size=training.train_size,
        test_size=training.test_size,
        features=tuple(FEATURE_COLUMNS),
    )

    champion = model_store.get_current_metadata(model_name)
    version = model_store.register(training.pipeline, metadata)

    promoted = champion is None or metadata.mae < champion.mae
    if promoted:
        model_store.promote(model_name, version)

    return RetrainResult(
        training=training,
        metadata=metadata,
        promoted=promoted,
        champion_mae=champion.mae if champion is not None else None,
    )
