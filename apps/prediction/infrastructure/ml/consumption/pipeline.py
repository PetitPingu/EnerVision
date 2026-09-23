"""Pipeline sklearn pour la prédiction de consommation.

Assemble le preprocessing (encodage de site_id) et le modèle de régression.
À utiliser avec les matrices X produites par features.build_features().
"""

from sklearn.base import RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES = ["site_id", "day_of_week"]
NUMERIC_FEATURES = ["hour", "minute"]


def build_preprocessor() -> ColumnTransformer:
    """Preprocessing partagé par tous les candidats (site_id one-hot, hour/minute
    passthrough) — voir infrastructure/ml/consumption/pipeline.py pour le pipeline
    par défaut et tests/manual/manual_benchmark_models.py pour le benchmark
    d'algorithmes qui réutilise ce même preprocessing."""
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            ("num", "passthrough", NUMERIC_FEATURES),
        ],
    )


def create_model_pipeline(
    n_estimators: int = 100,
    random_state: int = 42,
) -> Pipeline:
    """Construit un pipeline prêt à fit/predict sur le DataFrame X de build_features()."""
    return build_pipeline_for(
        RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)
    )


def build_pipeline_for(regressor: RegressorMixin) -> Pipeline:
    """Assemble le preprocessing partagé avec un régresseur candidat quelconque."""
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("model", regressor),
        ],
    )
