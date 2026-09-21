"""Script manuel : Postgres -> entrainement du modele d'etat -> registry.

Declenche a la demande le meme cycle que le job planifie
(retrain_state_if_better) : le candidat n'est promu en Production que s'il
bat le champion actuel (accuracy).

Usage (depuis apps/prediction, ou dans le conteneur `prediction`) :
    python tests/manual/manual_retrain_state.py

Variables d'environnement : DATABASE_URL, MINIO_*, MLFLOW_* (voir .env a la racine).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from application.state.retrain_state_if_better import retrain_state_if_better
from infrastructure.config import Config
from infrastructure.model_store import create_model_store
from infrastructure.training_data import create_state_training_data_reader


def main() -> None:
    print(f"Modele : {Config.STATE_MODEL_NAME}")
    print()

    result = retrain_state_if_better(
        data_reader=create_state_training_data_reader(),
        model_store=create_model_store(),
        model_name=Config.STATE_MODEL_NAME,
    )

    champion = result.champion_accuracy
    print("=== Reentrainement termine ===")
    print(f"  train      : {result.training.train_size} lignes")
    print(f"  test       : {result.training.test_size} lignes")
    print(f"  accuracy   : {result.training.accuracy:.3f}")
    print(f"  F1 macro   : {result.training.f1_macro:.3f}")
    print(f"  champion   : {'aucun' if champion is None else f'{champion:.3f}'}")
    print(f"  promu      : {'oui' if result.promoted else 'non (pas meilleur)'}")


if __name__ == "__main__":
    main()
