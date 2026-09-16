"""Script manuel : charge readings_curated depuis Postgres et entraine le modele.

Usage (depuis apps/prediction) :
    python tests/manual/manual_postgres_train.py

Variables d'environnement : DATABASE_URL (voir .env a la racine du monorepo).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.config import Config
from infrastructure.training_data import explore_training_data


if __name__ == "__main__":
    explore_training_data(Config.DATABASE_URL)
