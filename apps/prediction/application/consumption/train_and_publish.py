"""Use case : entraîner le modèle et le publier dans le stockage objet."""

from dataclasses import dataclass

from application.ports import ModelStorePort, SavedModelMetadata, TrainingDataPort
from infrastructure.model_store import utc_version_timestamp
from infrastructure.ml.consumption.features import FEATURE_COLUMNS
from infrastructure.ml.consumption.trainer import TrainingResult, train_model


@dataclass(frozen=True)
class PublishResult:
    """Résultat d'un entraînement + publication."""

    training: TrainingResult
    metadata: SavedModelMetadata
    object_prefix: str


def train_and_publish(
    data_reader: TrainingDataPort,
    model_store: ModelStorePort,
    model_name: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> PublishResult:
    """Charge les données, entraîne le pipeline et l'enregistre dans le store."""
    df = data_reader.fetch_training_data()
    if df.empty:
        raise ValueError("Aucune donnee d'entrainement disponible")

    training = train_model(df, test_size=test_size, random_state=random_state)
    metadata = SavedModelMetadata(
        model_name=model_name,
        trained_at=utc_version_timestamp(),
        metrics={"mae": training.mae, "rmse": training.rmse},
        train_size=training.train_size,
        test_size=training.test_size,
        features=tuple(FEATURE_COLUMNS),
    )
    object_prefix = model_store.save(training.pipeline, metadata)

    return PublishResult(
        training=training,
        metadata=metadata,
        object_prefix=object_prefix,
    )
