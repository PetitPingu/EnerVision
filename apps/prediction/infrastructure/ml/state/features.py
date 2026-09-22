"""Feature engineering pour le modèle de classification de l'état futur des
capteurs (data_quality : good/partial/degraded/critical).

X = site_id + heure (pas la minute, voir aggregate_hourly). Réutilise
extract_temporal_features() de features.py (régression consommation).
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
TEMPORAL_FEATURES = ["hour"]

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
            temporal[TEMPORAL_FEATURES].reset_index(drop=True),
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


# Nombre minimal de lectures "off" dans l'heure pour considérer le capteur
# en panne sur ce bucket horaire. > 1 (pas juste "au moins une fois") pour
# ignorer un blip isolé d'une minute, probablement du bruit, et ne garder
# que les pannes qui persistent un minimum dans l'heure.
MIN_OFF_READINGS_PER_HOUR = 2


def aggregate_hourly(
    df: pd.DataFrame,
    min_off_readings: int = MIN_OFF_READINGS_PER_HOUR,
) -> pd.DataFrame:
    """Agrège les lectures minute par minute en buckets horaires
    (site_id, heure) : un capteur est "off" pour cette heure si AU MOINS
    `min_off_readings` lectures de l'heure l'ont vu off, "on" sinon.

    À l'échelle de la minute, chaque panne est un événement quasi unique
    (une seule ligne par site et par minute dans tout l'historique) : le
    modèle ne peut apprendre aucun motif réel, seulement du bruit. À
    l'échelle de l'heure, la même panne devient un exemple que d'autres
    heures peuvent effectivement recouper - et c'est aussi le grain que
    /predict/state/range expose déjà (un point par heure). Le seuil (pas
    juste "au moins une fois") écarte en plus les anomalies isolées d'une
    seule lecture. Voir docs/state-model.md, section Limites.
    """
    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le DataFrame : {missing}")

    working = df.dropna(subset=[TARGET_COLUMN]).copy()
    working["timestamp"] = pd.to_datetime(working["timestamp"], format="ISO8601")
    working["_hour_bucket"] = working["timestamp"].dt.floor("h")

    rows = []
    for (site_id, hour_bucket), group in working.groupby(["site_id", "_hour_bucket"], sort=False):
        is_off = {
            column: bool(group[column].isna().sum() >= min_off_readings)
            for column in SENSOR_COLUMNS
        }
        row = {
            "site_id": site_id,
            "timestamp": hour_bucket.isoformat(),
            # Simple indicateur binaire (pas la taxonomie good/partial/
            # degraded/critical) : sert uniquement à stratifier le
            # train/test split (voir trainer.py), pas une vraie data_quality.
            "data_quality": "off" if any(is_off.values()) else "good",
        }
        for column in SENSOR_COLUMNS:
            row[column] = None if is_off[column] else 1.0
        rows.append(row)

    return pd.DataFrame(rows, columns=RAW_COLUMNS)
