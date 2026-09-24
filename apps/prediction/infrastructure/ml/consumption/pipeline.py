"""Pipeline sklearn pour la prédiction de consommation.

Assemble l'enrichissement site_type/weekend, le preprocessing (encodage des
catégorielles) et le modèle de régression. À utiliser avec les matrices X
produites par features.build_features().
"""

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

_WEEKEND_DAYS = {5, 6}  # samedi, dimanche (pandas .dt.dayofweek)

CATEGORICAL_FEATURES = ["site_id", "day_of_week", "site_type", "site_type_weekend"]
NUMERIC_FEATURES = ["hour", "minute", "is_weekend"]


class SiteTypeWeekendExpander(BaseEstimator, TransformerMixin):
    """Dérive is_weekend (depuis day_of_week) et l'interaction site_type x
    weekend (depuis site_id + day_of_week), pour que même un modèle linéaire
    (Ridge) puisse apprendre "ce type de site se comporte différemment le
    week-end" sans dépendre d'une colonne site_type fournie à l'inférence.

    /predict n'envoie que site_id (voir application/consumption/predict.py) :
    le fit() apprend une correspondance site_id -> site_type à partir des
    données d'entraînement (colonne site_type, voir
    infrastructure/ml/consumption/features.py:TRAINING_ONLY_COLUMNS) et le
    transform() s'appuie uniquement sur elle par la suite - jamais sur une
    colonne site_type fournie en entrée, pour un comportement identique à
    l'entraînement (évaluation sur x_test) et en service (/predict).
    Un site_id inconnu au fit reçoit "unknown" (même tolérance que
    OneHotEncoder(handle_unknown="ignore") pour les autres catégorielles).
    """

    def fit(self, x: pd.DataFrame, y=None):
        self.site_type_by_id_ = (
            x.groupby("site_id")["site_type"].first().to_dict() if "site_type" in x.columns else {}
        )
        return self

    def transform(self, x: pd.DataFrame) -> pd.DataFrame:
        x = x.copy()
        site_type = x["site_id"].map(self.site_type_by_id_).fillna("unknown")
        is_weekend = x["day_of_week"].isin(_WEEKEND_DAYS).astype(int)

        x["site_type"] = site_type
        x["is_weekend"] = is_weekend
        x["site_type_weekend"] = site_type + "_" + is_weekend.map({1: "weekend", 0: "weekday"})
        return x


def build_preprocessor() -> ColumnTransformer:
    """Preprocessing partagé par tous les candidats (catégorielles one-hot,
    hour/minute/is_weekend passthrough) — voir
    infrastructure/ml/consumption/pipeline.py pour le pipeline par défaut et
    tests/manual/manual_benchmark_models.py pour le benchmark d'algorithmes
    qui réutilise ce même preprocessing."""
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
    """Assemble l'enrichissement + le preprocessing partagés avec un régresseur
    candidat quelconque."""
    return Pipeline(
        steps=[
            ("site_type_weekend", SiteTypeWeekendExpander()),
            ("preprocessor", build_preprocessor()),
            ("model", regressor),
        ],
    )
