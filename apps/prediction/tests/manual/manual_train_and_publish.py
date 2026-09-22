"""Script manuel : Postgres -> entrainement -> MinIO (bucket models).

Usage (depuis apps/prediction) :
    python tests/manual/manual_train_and_publish.py

Variables d'environnement : DATABASE_URL, MINIO_* (voir .env a la racine).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from application.consumption.train_and_publish import train_and_publish
from infrastructure.config import Config
from infrastructure.model_store import create_model_store
from infrastructure.training_data import create_training_data_reader


def main() -> None:
    print(f"Source donnees : {Config.TRAINING_DATA_SOURCE}")
    print(f"Bucket modeles : {Config.MINIO_MODELS_BUCKET} @ {Config.MINIO_ENDPOINT}")
    print(f"Modele         : {Config.MODEL_NAME}")
    print()

    result = train_and_publish(
        data_reader=create_training_data_reader(),
        model_store=create_model_store(),
        model_name=Config.MODEL_NAME,
    )

    print("=== Publication reussie ===")
    print(f"  prefixe objet : {result.object_prefix}")
    print(f"  latest        : {Config.MODEL_NAME}/latest/model.joblib")
    print(f"  train         : {result.training.train_size} lignes")
    print(f"  test          : {result.training.test_size} lignes")
    print(f"  MAE           : {result.training.mae:.2f} kWh")
    print(f"  RMSE          : {result.training.rmse:.2f} kWh")


if __name__ == "__main__":
    main()
