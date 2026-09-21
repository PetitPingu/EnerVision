"""Entraînement du modèle d'état on/off des capteurs.

Orchestre state_features.build_features() / build_sensor_targets(), le split
train/test et l'évaluation du pipeline. Les métriques portent sur l'état
on/off de chaque capteur (accuracy + F1 macro, ce dernier adapté au
déséquilibre : un capteur est presque toujours "on").
"""

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from infrastructure.ml.state.features import build_features, build_sensor_targets
from infrastructure.ml.state.pipeline import create_model_pipeline


@dataclass(frozen=True)
class StateTrainingResult:
    """Résultat d'un entraînement : pipeline entraîné et métriques sur le
    test set, calculées sur l'ensemble des états on/off de capteurs."""

    pipeline: Pipeline
    accuracy: float
    f1_macro: float
    train_size: int
    test_size: int


def train_model(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> StateTrainingResult:
    """Entraîne le pipeline sur df et retourne le modèle + métriques
    (accuracy, F1 macro)."""
    x, y = build_features(df)
    sensors = build_sensor_targets(df)

    # Stratifié sur data_quality (pas sur les capteurs) pour garder les états
    # rares, donc les pannes, dans le jeu de test.
    stratify = y if y.nunique() > 1 else None
    x_train, x_test, s_train, s_test = train_test_split(
        x,
        sensors,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    pipeline = create_model_pipeline(random_state=random_state)
    pipeline.fit(x_train, s_train.to_numpy())

    predictions = pipeline.predict(x_test)
    expected = s_test.to_numpy().ravel()
    predicted = predictions.ravel()
    accuracy = accuracy_score(expected, predicted)
    f1_macro = f1_score(expected, predicted, average="macro", zero_division=0)

    return StateTrainingResult(
        pipeline=pipeline,
        accuracy=accuracy,
        f1_macro=f1_macro,
        train_size=len(x_train),
        test_size=len(x_test),
    )
