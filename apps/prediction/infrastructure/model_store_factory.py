"""Composition : choisit l'implémentation concrète de ModelStorePort."""

from application.ports import ModelStorePort
from infrastructure.config import Config
from infrastructure.minio_model_store import MinioModelStore


def create_model_store() -> ModelStorePort:
    """Instancie le stockage selon MODEL_STORE (minio pour l'instant)."""
    store = Config.MODEL_STORE

    if store == "minio":
        return MinioModelStore(
            endpoint=Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            bucket=Config.MINIO_MODELS_BUCKET,
            secure=Config.MINIO_SECURE,
        )

    raise ValueError(f"MODEL_STORE inconnu : {store}")
