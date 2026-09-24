"""Lit les données d'entraînement depuis readings_curated (Postgres).

Même stack que CuratedWriter (SQLAlchemy sync + db_schema) : lecture
inverse de l'upsert effectué par le worker ETL.
"""

import pandas as pd
from db_schema.models import ReadingCurated
from sqlalchemy import create_engine, func, select

from application.ports import TrainingDataPort
from infrastructure.ml.consumption.features import RAW_COLUMNS, build_features
from infrastructure.ml.consumption.trainer import TrainingResult, train_model


class PostgresTrainingDataReader(TrainingDataPort):
    """Charge les lectures curées prêtes pour features.build_features()."""

    def __init__(self, database_url: str, engine=None):
        self._engine = engine or create_engine(database_url)

    def fetch_row_counts(self) -> tuple[int, int]:
        """Retourne (total lignes table, lignes avec consumption_kwh non null)."""
        total_stmt = select(func.count()).select_from(ReadingCurated)
        filtered_stmt = (
            select(func.count())
            .select_from(ReadingCurated)
            .where(ReadingCurated.consumption_kwh.is_not(None))
        )
        with self._engine.connect() as conn:
            total = conn.scalar(total_stmt) or 0
            filtered = conn.scalar(filtered_stmt) or 0
        return total, filtered

    def fetch_training_data(self) -> pd.DataFrame:
        stmt = (
            select(
                ReadingCurated.site_id,
                ReadingCurated.timestamp,
                ReadingCurated.consumption_kwh,
                ReadingCurated.site_type,
            )
            .where(ReadingCurated.consumption_kwh.is_not(None))
            .order_by(ReadingCurated.timestamp)
        )
        df = pd.read_sql(stmt, self._engine)
        return df[RAW_COLUMNS]


def explore_training_data(
    database_url: str,
    test_size: float = 0.25,
    random_state: int = 42,
) -> TrainingResult | None:
    """Usage manuel : stats + entrainement (meme format que tests/mon_test.py)."""
    reader = PostgresTrainingDataReader(database_url)
    total_rows, filtered_rows = reader.fetch_row_counts()
    df = reader.fetch_training_data()

    print("=== Donnees chargees depuis readings_curated ===")
    print(
        f"  total table: {total_rows} lignes  |  "
        f"apres filtre consumption_kwh: {filtered_rows} lignes"
    )
    print()

    if df.empty:
        print("Aucune donnee exploitable. Arret.")
        return None

    print("=== DataFrame d'entree (5 premieres lignes) ===")
    print(df.head())
    print()

    x, y = build_features(df)

    print("=== X (features, 5 premieres lignes) ===")
    print(x.head())
    print()

    print("=== y (target, 5 premieres lignes) ===")
    print(y.head())
    print(f"  ... {len(y)} lignes au total")
    print()

    result = train_model(df, test_size=test_size, random_state=random_state)

    print("=== Entrainement ===")
    print(f"  train: {result.train_size} lignes  |  test: {result.test_size} lignes")
    print(f"  MAE:  {result.mae:.2f} kWh")
    print(f"  RMSE: {result.rmse:.2f} kWh")
    print()

    predictions = result.pipeline.predict(x)
    print("=== Predictions sur tout le jeu (5 premieres lignes) ===")
    for i, (actual, predicted) in enumerate(zip(y.head(), predictions[:5], strict=True)):
        print(f"  ligne {i}: reel={actual:.2f} kWh -> predit={predicted:.2f} kWh")

    return result
