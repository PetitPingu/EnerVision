"""Composition : choisit l'implémentation concrète de ModelStorePort.

Une seule paire d'implémentations (Minio/MlflowModelStore) sert les deux
modèles du service (régression consommation et classification d'état) :
ModelStorePort ne connaît que SavedModelMetadata.metrics (dict générique),
donc rien à dupliquer côté stockage pour un second modèle - seul
model_name (voir Config.MODEL_NAME / Config.STATE_MODEL_NAME) les distingue.
"""

from application.ports import ModelStorePort
from infrastructure.config import Config
from infrastructure.model_store.minio_store import MinioModelStore
from infrastructure.model_store.mlflow_store import MlflowModelStore


def create_model_store() -> ModelStorePort:
    """Instancie le stockage selon MODEL_STORE (minio ou mlflow)."""
    store = Config.MODEL_STORE

    if store == "minio":
        return MinioModelStore(
            endpoint=Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            bucket=Config.MINIO_MODELS_BUCKET,
            secure=Config.MINIO_SECURE,
        )

    if store == "mlflow":
        return MlflowModelStore(tracking_uri=Config.MLFLOW_TRACKING_URI)

    raise ValueError(f"MODEL_STORE inconnu : {store}")
