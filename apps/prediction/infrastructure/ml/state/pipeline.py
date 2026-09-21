"""Pipeline sklearn pour la prédiction de l'état on/off des capteurs.

Assemble le preprocessing (encodage de site_id) et un classifieur
multi-sorties : une sortie (1 = on, 0 = off) par colonne de SENSOR_COLUMNS.
L'état global du site (good/partial/degraded/critical) n'est pas appris : il
se déduit du nombre de capteurs prédits off, voir
application.state.predict_state.derive_state().
"""

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CATEGORICAL_FEATURES = ["site_id"]
NUMERIC_FEATURES = ["hour", "minute"]


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
