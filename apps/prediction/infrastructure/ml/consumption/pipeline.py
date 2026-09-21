"""Pipeline sklearn pour la prédiction de consommation.

Assemble le preprocessing (encodage de site_id) et le modèle de régression.
À utiliser avec les matrices X produites par features.build_features().
"""

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES = ["site_id"]
NUMERIC_FEATURES = ["hour", "minute"]


def create_model_pipeline(
    n_estimators: int = 100,
    random_state: int = 42,
) -> Pipeline:
    """Construit un pipeline prêt à fit/predict sur le DataFrame X de build_features()."""
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
                RandomForestRegressor(
                    n_estimators=n_estimators,
                    random_state=random_state,
                ),
            ),
        ],
    )
