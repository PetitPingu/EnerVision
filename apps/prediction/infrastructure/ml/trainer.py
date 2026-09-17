"""Entraînement du modèle de prédiction de consommation.

Orchestre build_features(), le split train/test et l'évaluation du pipeline.
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from infrastructure.ml.features import build_features
from infrastructure.ml.pipeline import create_model_pipeline


@dataclass(frozen=True)
class TrainingResult:
    """Résultat d'un entraînement : pipeline entraîné et métriques sur le test set."""

    pipeline: Pipeline
    mae: float
    rmse: float
    train_size: int
    test_size: int


def train_model(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> TrainingResult:
    """Entraîne le pipeline sur df et retourne le modèle + métriques (MAE, RMSE)."""
    x, y = build_features(df)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    pipeline = create_model_pipeline(random_state=random_state)
    pipeline.fit(x_train, y_train)

    predictions = pipeline.predict(x_test)
    mae = mean_absolute_error(y_test, predictions)
    rmse = root_mean_squared_error(y_test, predictions)

    return TrainingResult(
        pipeline=pipeline,
        mae=mae,
        rmse=rmse,
        train_size=len(x_train),
        test_size=len(x_test),
    )
