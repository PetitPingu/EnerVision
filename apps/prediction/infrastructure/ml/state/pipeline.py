"""Pipeline sklearn pour la prédiction de l'état on/off des capteurs.

Assemble le preprocessing (encodage de site_id) et un classifieur
multi-sorties : une sortie (1 = on, 0 = off) par colonne de SENSOR_COLUMNS.
Pas d'état global du site appris : c'est le front qui affiche chaque
capteur individuellement, voir apps/prediction/docs/state-model.md.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES = ["site_id"]
NUMERIC_FEATURES = ["hour"]


def create_model_pipeline(
    n_estimators: int = 100,
    random_state: int = 42,
) -> Pipeline:
    """Construit un pipeline prêt à fit(x, sensors) / predict(x), avec x issu
    de features.build_features() et sensors de features.build_sensor_targets()."""
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            ("num", "passthrough", NUMERIC_FEATURES),
        ],
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                MultiOutputClassifier(
                    RandomForestClassifier(
                        n_estimators=n_estimators,
                        random_state=random_state,
                    )
                ),
            ),
        ],
    )


def predict_with_confidence(pipeline: Pipeline, x: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Prédit l'état on/off de chaque capteur (0/1) et la confiance du
    modèle dans cette prédiction (probabilité de la classe prédite, entre
    0 et 1 — pas un intervalle de confiance statistique).

    Retourne deux tableaux de forme (n_samples, n_sensors). Un capteur qui
    n'a jamais été vu "off" à l'entraînement n'a qu'une classe côté
    RandomForestClassifier : sa confiance est alors 1.0 par construction
    (le modèle n'a jamais eu l'occasion d'hésiter).
    """
    predictions = np.asarray(pipeline.predict(x))
    proba_per_sensor = pipeline.predict_proba(x)
    estimators = pipeline.named_steps["model"].estimators_

    confidences = np.ones_like(predictions, dtype=float)
    for sensor_index, (estimator, proba) in enumerate(zip(estimators, proba_per_sensor)):
        classes = list(estimator.classes_)
        for row_index in range(predictions.shape[0]):
            predicted_class = predictions[row_index, sensor_index]
            if predicted_class in classes:
                confidences[row_index, sensor_index] = proba[row_index, classes.index(predicted_class)]

    return predictions, confidences
