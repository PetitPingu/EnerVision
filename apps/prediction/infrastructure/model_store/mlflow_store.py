"""Persistance des modèles entraînés via MLflow (Tracking + Model Registry).

Alternative à MinioModelStore (MODEL_STORE=mlflow) : au lieu d'écrire les
octets directement dans MinIO via le SDK minio, ce store délègue à MLflow,
qui gère lui-même le stockage physique (même bucket MinIO en interne,
configuré côté serveur - voir mlflow/entrypoint.sh) et ajoute l'historique
des runs et le Model Registry.

L'alias "current" (réassigné à chaque save()) joue le même rôle que le
pointeur {model_name}/latest/ de MinioModelStore : toujours pointer vers le
dernier modèle entraîné, sans dépendre d'un numéro de version à suivre
manuellement. Pas "latest" : ce nom est réservé par MLflow (conflit avec la
notion historique de "dernière version"), il lève une erreur à la création.
"""

import mlflow
import mlflow.sklearn
from mlflow.entities import Run
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from sklearn.pipeline import Pipeline

from application.ports import ModelStorePort, SavedModelMetadata

_ALIAS = "current"


class MlflowModelStore(ModelStorePort):
    """Enregistre les modèles dans MLflow (Tracking + Model Registry)."""

    def __init__(self, tracking_uri: str, client: MlflowClient | None = None):
        mlflow.set_tracking_uri(tracking_uri)
        self._client = client or MlflowClient(tracking_uri=tracking_uri)

    def save(self, pipeline: Pipeline, metadata: SavedModelMetadata) -> str:
        version = self.register(pipeline, metadata)
        self.promote(metadata.model_name, version)

        return f"{metadata.model_name}/{version}"

    def register(self, pipeline: Pipeline, metadata: SavedModelMetadata) -> str:
        """Enregistre une nouvelle version dans le Registry sans toucher à
        l'alias `current` - voir promote()."""
        with mlflow.start_run(run_name=metadata.trained_at):
            mlflow.log_params(
                {
                    "trained_at": metadata.trained_at,
                    "train_size": metadata.train_size,
                    "test_size": metadata.test_size,
                    "features": ",".join(metadata.features),
                }
            )
            mlflow.log_metrics({"mae": metadata.mae, "rmse": metadata.rmse})

            model_info = mlflow.sklearn.log_model(
                pipeline,
                name="model",
                registered_model_name=metadata.model_name,
                skops_trusted_types=["sklearn.tree._tree.Tree"],
            )

        return model_info.registered_model_version

    def promote(self, model_name: str, version: str) -> None:
        self._client.set_registered_model_alias(model_name, _ALIAS, version)

    def load_latest(self, model_name: str) -> tuple[Pipeline, SavedModelMetadata]:
        model_version = self._client.get_model_version_by_alias(model_name, _ALIAS)
        run = self._client.get_run(model_version.run_id)

        pipeline = mlflow.sklearn.load_model(f"models:/{model_name}@{_ALIAS}")
        metadata = _metadata_from_run(model_name, run)

        return pipeline, metadata

    def get_current_metadata(self, model_name: str) -> SavedModelMetadata | None:
        """Métadonnées du modèle actuellement servi (alias `current`), ou
        None si {model_name} n'a encore jamais été promu."""
        try:
            model_version = self._client.get_model_version_by_alias(model_name, _ALIAS)
        except MlflowException as exc:
            if exc.error_code == "RESOURCE_DOES_NOT_EXIST":
                return None
            raise

        run = self._client.get_run(model_version.run_id)
        return _metadata_from_run(model_name, run)


def _metadata_from_run(model_name: str, run: Run) -> SavedModelMetadata:
    """Reconstruit SavedModelMetadata depuis les params/metrics du run - MLflow
    n'a pas de sidecar JSON comme MinioModelStore, tout vit dans le run."""
    params, metrics = run.data.params, run.data.metrics
    features = tuple(params["features"].split(",")) if params.get("features") else ()

    # mae/rmse/train_size/test_size n'ont pas de valeur par défaut sensée -
    # un run qui ne les a pas (alias repointé à la main vers un run externe,
    # par ex.) est une entrée de Registry corrompue : on veut un KeyError
    # explicite ici plutôt qu'un 0.0/0 silencieux et trompeur.
    return SavedModelMetadata(
        model_name=model_name,
        trained_at=params.get("trained_at", ""),
        mae=float(metrics["mae"]),
        rmse=float(metrics["rmse"]),
        train_size=int(params["train_size"]),
        test_size=int(params["test_size"]),
        features=features,
    )
