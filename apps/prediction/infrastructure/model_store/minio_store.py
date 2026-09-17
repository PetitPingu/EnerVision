"""Persistance des modèles sklearn dans le bucket MinIO models.

Même stack que RawWriter (SDK minio) : un répertoire versionné par run
et un pointeur latest/ pour le chargement au démarrage du service.
"""

import json
from datetime import datetime, timezone
from io import BytesIO

import joblib
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
from sklearn.pipeline import Pipeline

from application.ports import ModelStorePort, SavedModelMetadata


class MinioModelStore(ModelStorePort):
    """Sérialise les pipelines en joblib et les dépose dans MinIO."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
        client: Minio | None = None,
    ):
        self._bucket = bucket
        self._client = client or Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def save(self, pipeline: Pipeline, metadata: SavedModelMetadata) -> str:
        version = self.register(pipeline, metadata)
        self.promote(metadata.model_name, version)

        return version

    def register(self, pipeline: Pipeline, metadata: SavedModelMetadata) -> str:
        """Écrit la version sous {model_name}/{trained_at}/ sans toucher au
        pointeur latest/ - voir promote()."""
        version_prefix = f"{metadata.model_name}/{metadata.trained_at}"
        self._put_pipeline(f"{version_prefix}/model.joblib", pipeline)
        self._put_metadata(f"{version_prefix}/metadata.json", metadata)

        return version_prefix

    def promote(self, model_name: str, version: str) -> None:
        """Copie {version}/ vers latest/ côté serveur (pas de ré-upload)."""
        latest_prefix = f"{model_name}/latest"
        for filename in ("model.joblib", "metadata.json"):
            self._client.copy_object(
                self._bucket,
                f"{latest_prefix}/{filename}",
                CopySource(self._bucket, f"{version}/{filename}"),
            )

    def load_latest(self, model_name: str) -> tuple[Pipeline, SavedModelMetadata]:
        pipeline = self._get_pipeline(f"{model_name}/latest/model.joblib")
        metadata = self._get_metadata(f"{model_name}/latest/metadata.json")
        return pipeline, metadata

    def get_current_metadata(self, model_name: str) -> SavedModelMetadata | None:
        try:
            return self._get_metadata(f"{model_name}/latest/metadata.json")
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return None
            raise

    def _put_pipeline(self, object_key: str, pipeline: Pipeline) -> None:
        buffer = BytesIO()
        joblib.dump(pipeline, buffer)
        payload = buffer.getvalue()
        payload_buffer = BytesIO(payload)
        self._client.put_object(
            self._bucket,
            object_key,
            payload_buffer,
            length=len(payload),
            content_type="application/octet-stream",
        )

    def _put_metadata(self, object_key: str, metadata: SavedModelMetadata) -> None:
        payload = json.dumps(
            {
                "model_name": metadata.model_name,
                "trained_at": metadata.trained_at,
                "mae": metadata.mae,
                "rmse": metadata.rmse,
                "train_size": metadata.train_size,
                "test_size": metadata.test_size,
                "features": list(metadata.features),
            },
            indent=2,
        ).encode("utf-8")
        payload_buffer = BytesIO(payload)
        self._client.put_object(
            self._bucket,
            object_key,
            payload_buffer,
            length=len(payload),
            content_type="application/json",
        )

    def _get_object_bytes(self, object_key: str) -> bytes:
        response = self._client.get_object(self._bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            release_conn = getattr(response, "release_conn", None)
            if release_conn is not None:
                release_conn()

    def _get_pipeline(self, object_key: str) -> Pipeline:
        return joblib.load(BytesIO(self._get_object_bytes(object_key)))

    def _get_metadata(self, object_key: str) -> SavedModelMetadata:
        data = json.loads(self._get_object_bytes(object_key).decode("utf-8"))

        return SavedModelMetadata(
            model_name=data["model_name"],
            trained_at=data["trained_at"],
            mae=float(data["mae"]),
            rmse=float(data["rmse"]),
            train_size=int(data["train_size"]),
            test_size=int(data["test_size"]),
            features=tuple(data["features"]),
        )


def utc_version_timestamp() -> str:
    """Horodatage safe pour les clés objet MinIO (pas de ':' ni espaces)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
