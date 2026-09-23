"""Feature engineering pour le modèle de prédiction de consommation.

Transforme les lectures brutes (table consumption_readings) en matrices
d'entraînement :
  - X : site_id + heure/minute
  - y : consumption_kwh (variable à prédire)

Historique court (~10 jours) : heure, minute et jour de la semaine sont
extraits du timestamp (pas de mois/année, non significatif sur un
historique aussi court).

NOTE (test A/B) : temperature_celsius temporairement retirée des features.
"""

import pandas as pd

# Colonnes minimales attendues en entrée (résultat d'une requête Postgres).
# site_type n'est pas fourni par /predict (voir application/consumption/predict.py)
# - seulement par les données d'entraînement - le pipeline apprend la
# correspondance site_id -> site_type au fit (SiteTypeWeekendExpander,
# infrastructure/ml/consumption/pipeline.py) pour ne pas en dépendre à l'inférence.
RAW_COLUMNS = [
    "site_id",
    "timestamp",
    "consumption_kwh",
    "site_type",
]

# Composantes temporelles extraites du timestamp.
# day_of_week : 0=lundi .. 6=dimanche (pandas .dt.dayofweek) — non ordinal,
# traité en catégoriel dans le pipeline (voir infrastructure/ml/consumption/pipeline.py).
TEMPORAL_FEATURES = ["hour", "minute", "day_of_week"]

# Colonnes fournies par /predict (le "contrat" d'entrée du modèle à l'inférence).
FEATURE_COLUMNS = ["site_id", *TEMPORAL_FEATURES]

# site_type : présent uniquement dans les données d'entraînement, consommé par
# SiteTypeWeekendExpander.fit() pour construire la correspondance site_id ->
# site_type (voir infrastructure/ml/consumption/pipeline.py).
TRAINING_ONLY_COLUMNS = ["site_type"]

# Variable cible (consommation à prédire).
TARGET_COLUMN = "consumption_kwh"


def extract_temporal_features(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """Décompose le timestamp en heure, minutes et jour de la semaine."""
    # ISO8601 : gère les formats mixtes (avec ou sans microsecondes).
    ts = pd.to_datetime(df[timestamp_col], format="ISO8601")
    return pd.DataFrame(
        {
            "hour": ts.dt.hour,
            "minute": ts.dt.minute,
            "day_of_week": ts.dt.dayofweek,
        },
        index=df.index,
    )


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Construit X (features) et y (target) à partir des lectures brutes.

    Les lignes sans consumption_kwh sont exclues (lectures critical / null).
    """
    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le DataFrame : {missing}")

    cleaned = df.dropna(subset=[TARGET_COLUMN]).copy()
    temporal = extract_temporal_features(cleaned)

    x = pd.concat(
        [
            cleaned[["site_id"]].reset_index(drop=True),
            temporal.reset_index(drop=True),
            cleaned[TRAINING_ONLY_COLUMNS].reset_index(drop=True),
        ],
        axis=1,
    )
    y = cleaned[TARGET_COLUMN].reset_index(drop=True)

    return x, y
