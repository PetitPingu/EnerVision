"""Migration ponctuelle : importe le dernier modèle MinioModelStore existant
dans le Model Registry MLflow, sans ré-entraîner - préserve exactement le
modèle et les métriques déjà obtenus (par ex. par des collègues) avant la
bascule MODEL_STORE=mlflow (voir docs/model-registry.md).

Usage (depuis apps/prediction) :
    python tests/manual/manual_migrate_minio_to_mlflow.py [model_name]

model_name par défaut : Config.MODEL_NAME ("energy-consumption").
Variables d'environnement : MINIO_* (source) + MLFLOW_TRACKING_URI (cible),
voir .env à la racine.

Idempotent : relançable sans effet de bord - crée juste une nouvelle version
dans le Registry à chaque exécution (l'alias "current" reste sur la
dernière), ne modifie jamais MinIO.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.config import Config
from infrastructure.model_store.minio_store import MinioModelStore
from infrastructure.model_store.mlflow_store import MlflowModelStore


def main() -> None:
    model_name = sys.argv[1] if len(sys.argv) > 1 else Config.MODEL_NAME

    source = MinioModelStore(
        endpoint=Config.MINIO_ENDPOINT,
        access_key=Config.MINIO_ACCESS_KEY,
        secret_key=Config.MINIO_SECRET_KEY,
        bucket=Config.MINIO_MODELS_BUCKET,
        secure=Config.MINIO_SECURE,
    )
    destination = MlflowModelStore(tracking_uri=Config.MLFLOW_TRACKING_URI)

    print(f"Lecture de '{model_name}/latest' depuis MinIO ({Config.MINIO_MODELS_BUCKET} @ {Config.MINIO_ENDPOINT})...")
    pipeline, metadata = source.load_latest(model_name)
    print(f"  trained_at={metadata.trained_at}  mae={metadata.mae:.2f}  rmse={metadata.rmse:.2f}")
    print(f"  train_size={metadata.train_size}  test_size={metadata.test_size}  features={metadata.features}")

    print(f"Enregistrement dans le Model Registry MLflow ({Config.MLFLOW_TRACKING_URI})...")
    prefix = destination.save(pipeline, metadata)

    print(f"OK - {prefix}, alias 'current' pointe dessus. MinIO n'a pas été modifié.")


if __name__ == "__main__":
    main()
