"""Feature engineering pour le modèle de prédiction de consommation.

Transforme les lectures brutes (table consumption_readings) en matrices
d'entraînement :
  - X : site_id + heure/minute
  - y : consumption_kwh (variable à prédire)

Historique court (~10 jours) : seules l'heure et les minutes sont extraites
du timestamp (pas de jour/mois/année).

NOTE (test A/B) : temperature_celsius temporairement retirée des features.
"""

import pandas as pd

# Colonnes minimales attendues en entrée (résultat d'une requête Postgres).
RAW_COLUMNS = [
    "site_id",
    "timestamp",
    "consumption_kwh",
]

# Composantes temporelles extraites du timestamp.
TEMPORAL_FEATURES = ["hour", "minute"]

# Colonnes utilisées comme features par le modèle.
FEATURE_COLUMNS = ["site_id", *TEMPORAL_FEATURES]

# Variable cible (consommation à prédire).
TARGET_COLUMN = "consumption_kwh"


def extract_temporal_features(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """Décompose le timestamp en heure et minutes."""
    # ISO8601 : gère les formats mixtes (avec ou sans microsecondes).
    ts = pd.to_datetime(df[timestamp_col], format="ISO8601")
    return pd.DataFrame(
        {
            "hour": ts.dt.hour,
            "minute": ts.dt.minute,
        },
        index=df.index,
    )


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Construit X (features) et y (target) à partir des lectures brutes.

    Les lignes sans consumption_kwh sont exclues (lectures critical / null).
    Le filtre data_quality='good' est attendu en amont (requête SQL).
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
        ],
        axis=1,
    )
    y = cleaned[TARGET_COLUMN].reset_index(drop=True)

    return x, y
