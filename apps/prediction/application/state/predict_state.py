"""Use case : prédire l'état on/off de chaque capteur d'un site à partir du
dernier modèle publié, puis en déduire l'état global (data_quality) selon le
nombre de capteurs prédits off (voir derive_state)."""

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from application.ports import ModelStorePort, SavedModelMetadata
from infrastructure.ml.state.features import FEATURE_COLUMNS, SENSOR_COLUMNS


# Nombre de capteurs prédits off à partir duquel le site bascule dans l'état
# donné. Règle métier volontairement hors du modèle : elle s'ajuste ici sans
# ré-entraîner. 0 capteur off = good.
CRITICAL_MIN_OFF = 4
DEGRADED_MIN_OFF = 3
PARTIAL_MIN_OFF = 1


def derive_state(off_count: int) -> str:
    """État global (good/partial/degraded/critical) d'un site selon le nombre
    de capteurs prédits off."""
    if off_count >= CRITICAL_MIN_OFF:
        return "critical"
    if off_count >= DEGRADED_MIN_OFF:
        return "degraded"
    if off_count >= PARTIAL_MIN_OFF:
        return "partial"
    return "good"


class StateModelNotLoadedError(Exception):
    """Le modèle d'état demandé est indisponible dans le store."""


@dataclass(frozen=True)
class StatePredictionResult:
    """Résultat d'une inférence d'état sur un site et un instant cible."""

    site_id: str
    target_timestamp: datetime
    predicted_state: str
    model_version: str
    # "on"/"off" prédit par capteur ; vide pour un ancien modèle qui prédisait
    # directement l'état global.
    sensors: dict[str, str] = field(default_factory=dict)


def predict_state(
    model_store: ModelStorePort,
    model_name: str,
    site_id: str,
    target_timestamp: datetime,
) -> StatePredictionResult:
    """Charge le dernier modèle d'état, prédit chaque capteur on/off pour le
    site et l'instant donnés, puis en déduit l'état global."""
    pipeline, metadata = _load_latest_model(model_store, model_name)
    x = _build_prediction_input(site_id, target_timestamp)
    prediction = np.asarray(pipeline.predict(x))[0]

    if prediction.ndim == 0:
        # Ancien modèle : une seule sortie, l'état global directement.
        sensors: dict[str, str] = {}
        predicted_state = str(prediction)
    else:
        sensors = {
            name: "on" if value else "off"
            for name, value in zip(SENSOR_COLUMNS, prediction)
        }
        predicted_state = derive_state(list(sensors.values()).count("off"))

    return StatePredictionResult(
        site_id=site_id,
        target_timestamp=target_timestamp,
        predicted_state=predicted_state,
        model_version=metadata.trained_at,
        sensors=sensors,
    )


def _load_latest_model(
    model_store: ModelStorePort,
    model_name: str,
) -> tuple[Pipeline, SavedModelMetadata]:
    try:
        return model_store.load_latest(model_name)
    except Exception as exc:
        raise StateModelNotLoadedError(
            f"Impossible de charger le modele d'etat '{model_name}'"
        ) from exc


def _build_prediction_input(site_id: str, target_timestamp: datetime) -> pd.DataFrame:
    """Construit les features attendues par le pipeline sklearn."""
    return pd.DataFrame(
        [
            {
                "site_id": site_id,
                "hour": target_timestamp.hour,
                "minute": target_timestamp.minute,
            }
        ],
        columns=FEATURE_COLUMNS,
    )
