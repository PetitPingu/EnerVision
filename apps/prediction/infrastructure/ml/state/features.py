"""Feature engineering pour le modèle de classification de l'état futur des
capteurs (data_quality : good/partial/degraded/critical).

Même approche que features.py (régression consommation) : X = site_id +
heure/minute, seule la cible change (data_quality au lieu de
consumption_kwh). Réutilise extract_temporal_features().
"""

import pandas as pd

from infrastructure.ml.consumption.features import extract_temporal_features

# Un capteur par mesure de readings_curated : on = valeur présente, off =
# valeur nulle (capteur en panne / donnée manquante).
SENSOR_COLUMNS = [
    "consumption_kw",
    "voltage_v",
    "current_a",
    "power_factor",
    "temperature_celsius",
    "humidity_percent",
]

# Colonnes minimales attendues en entrée (résultat d'une requête Postgres).
RAW_COLUMNS = [
    "site_id",
    "timestamp",
    "data_quality",
    *SENSOR_COLUMNS,
]

# Composantes temporelles extraites du timestamp.
TEMPORAL_FEATURES = ["hour", "minute"]

# Colonnes utilisées comme features par le modèle.
FEATURE_COLUMNS = ["site_id", *TEMPORAL_FEATURES]

# Variable cible (état du capteur à prédire).
TARGET_COLUMN = "data_quality"

# Classes possibles, dans l'ordre attendu par le worker ETL (voir
# apps/etl_worker) - sert de garde-fou à l'entraînement (build_features).
STATE_CLASSES = ["good", "partial", "degraded", "critical"]


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Construit X (features) et y (target) à partir des lectures curées.

    Les lignes sans data_quality sont exclues.
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


def build_sensor_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Construit l'état on/off de chaque capteur (1 = on, 0 = off), aligné
    ligne à ligne sur build_features() (mêmes lignes exclues)."""
    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le DataFrame : {missing}")

    cleaned = df.dropna(subset=[TARGET_COLUMN])
    return cleaned[SENSOR_COLUMNS].notna().astype(int).reset_index(drop=True)
