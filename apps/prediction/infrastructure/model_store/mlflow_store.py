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
        with mlflow.start_run(run_name=metadata.trained_at) as run:
            mlflow.log_params(
                {
                    "trained_at": metadata.trained_at,
                    "train_size": metadata.train_size,
                    "test_size": metadata.test_size,
                    "features": ",".join(metadata.features),
                }
            )
            mlflow.log_metrics({"mae": metadata.mae, "rmse": metadata.rmse})
            mlflow.sklearn.log_model(pipeline, artifact_path="model")
            run_id = run.info.run_id

        model_version = mlflow.register_model(
            model_uri=f"runs:/{run_id}/model", name=metadata.model_name
        )
        self._client.set_registered_model_alias(metadata.model_name, _ALIAS, model_version.version)

        return f"{metadata.model_name}/{model_version.version}"

    def load_latest(self, model_name: str) -> tuple[Pipeline, SavedModelMetadata]:
        model_version = self._client.get_model_version_by_alias(model_name, _ALIAS)
        run = self._client.get_run(model_version.run_id)

        pipeline = mlflow.sklearn.load_model(f"models:/{model_name}@{_ALIAS}")
        metadata = _metadata_from_run(model_name, run)

        return pipeline, metadata


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
