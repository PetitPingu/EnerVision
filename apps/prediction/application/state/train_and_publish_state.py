"""Use case : entraîner le modèle d'état et le publier dans le stockage
objet (premier entraînement, sans comparaison à un champion - voir
retrain_state_if_better pour le ré-entraînement planifié)."""

from dataclasses import dataclass

from application.ports import ModelStorePort, SavedModelMetadata, StateTrainingDataPort
from infrastructure.ml.state.features import FEATURE_COLUMNS
from infrastructure.ml.state.trainer import StateTrainingResult, train_model
from infrastructure.model_store import utc_version_timestamp


@dataclass(frozen=True)
class StatePublishResult:
    """Résultat d'un entraînement + publication du modèle d'état."""

    training: StateTrainingResult
    metadata: SavedModelMetadata
    object_prefix: str


def train_and_publish_state(
    data_reader: StateTrainingDataPort,
    model_store: ModelStorePort,
    model_name: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> StatePublishResult:
    """Charge les données, entraîne le pipeline de classification et
    l'enregistre dans le store."""
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
    object_prefix = model_store.save(training.pipeline, metadata)

    return StatePublishResult(
        training=training,
        metadata=metadata,
        object_prefix=object_prefix,
    )
