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

import tempfile
import threading

import mlflow
import mlflow.sklearn
from mlflow.entities import Run
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from sklearn.pipeline import Pipeline

from application.ports import ModelStorePort, SavedModelMetadata

_ALIAS = "current"

# Au niveau du module et pas de l'instance : l'API crée un nouveau store à
# chaque requête (create_model_store()). Une entrée par (tracking_uri,
# model_name) : (run_id, pipeline, metadata) de la dernière version chargée.
# run_id plutôt que le numéro de version, unique même entre deux backends
# MLflow (tests : une base sqlite jetable par test, versions toutes à "1").
_LOADED_MODELS: dict[tuple[str, str], tuple[str, Pipeline, SavedModelMetadata]] = {}
_LOAD_LOCK = threading.Lock()


class MlflowModelStore(ModelStorePort):
    """Enregistre les modèles dans MLflow (Tracking + Model Registry)."""

    def __init__(self, tracking_uri: str, client: MlflowClient | None = None):
        mlflow.set_tracking_uri(tracking_uri)
        self._tracking_uri = tracking_uri
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
            mlflow.log_metrics(metadata.metrics)

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
        """Modèle pointé par l'alias `current`, gardé en mémoire tant que
        l'alias ne change pas.

        Seule la résolution de l'alias (appel léger au Registry) est faite à
        chaque requête : une promotion reste visible immédiatement, sans
        redémarrage. Le téléchargement des artefacts n'a lieu qu'au premier
        appel ou après une promotion, dans un dossier temporaire supprimé
        aussitôt - sans dst_path, MLflow crée un nouveau dossier temporaire
        à chaque load_model() et ne le nettoie jamais (35 Go accumulés dans
        le conteneur prediction, disque du serveur saturé le 23/09/2026).
        """
        model_version = self._client.get_model_version_by_alias(model_name, _ALIAS)
        cache_key = (self._tracking_uri, model_name)

        cached = _LOADED_MODELS.get(cache_key)
        if cached is not None and cached[0] == model_version.run_id:
            return cached[1], cached[2]

        with _LOAD_LOCK:
            # Un autre thread a pu charger cette même version pendant
            # l'attente du verrou (requêtes concurrentes juste après une
            # promotion) : ne pas la re-télécharger.
            cached = _LOADED_MODELS.get(cache_key)
            if cached is not None and cached[0] == model_version.run_id:
                return cached[1], cached[2]

            run = self._client.get_run(model_version.run_id)
            with tempfile.TemporaryDirectory() as dst_path:
                # Version explicite plutôt que l'alias : si l'alias bouge
                # entre les deux appels, pipeline et métadonnées restent
                # ceux de la même version.
                pipeline = mlflow.sklearn.load_model(
                    f"models:/{model_name}/{model_version.version}", dst_path=dst_path
                )
            metadata = _metadata_from_run(model_name, run)

            _LOADED_MODELS[cache_key] = (model_version.run_id, pipeline, metadata)

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

    # train_size/test_size n'ont pas de valeur par défaut sensée - un run qui
    # ne les a pas (alias repointé à la main vers un run externe, par ex.)
    # est une entrée de Registry corrompue : on veut un KeyError explicite
    # ici plutôt qu'un 0 silencieux et trompeur.
    return SavedModelMetadata(
        model_name=model_name,
        trained_at=params.get("trained_at", ""),
        metrics={key: float(value) for key, value in metrics.items()},
        train_size=int(params["train_size"]),
        test_size=int(params["test_size"]),
        features=features,
    )
