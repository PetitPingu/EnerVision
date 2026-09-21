"""Use case : prédire l'état on/off de chaque capteur d'un site à partir du
dernier modèle de classification publié."""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from application.ports import ModelStorePort, SavedModelMetadata
from infrastructure.ml.state.features import FEATURE_COLUMNS, SENSOR_COLUMNS


class StateModelNotLoadedError(Exception):
    """Le modèle d'état demandé est indisponible dans le store."""


@dataclass(frozen=True)
class StatePredictionResult:
    """Résultat d'une inférence d'état sur un site et un instant cible."""

    site_id: str
    target_timestamp: datetime
    # "on"/"off" prédit pour chaque capteur (clés = SENSOR_COLUMNS).
    sensors: dict[str, str]
    model_version: str


def predict_state(
    model_store: ModelStorePort,
    model_name: str,
    site_id: str,
    target_timestamp: datetime,
) -> StatePredictionResult:
    """Charge le dernier modèle d'état et prédit l'état on/off de chaque
    capteur pour le site et l'instant donnés."""
    pipeline, metadata = _load_latest_model(model_store, model_name)
    x = _build_prediction_input(site_id, target_timestamp)
    prediction = np.asarray(pipeline.predict(x))[0]

    if prediction.ndim == 0:
        # Ancien modèle qui prédisait un état global : plus exploitable tel quel.
        raise StateModelNotLoadedError(
            f"Le modele '{model_name}' est un ancien modele, un reentrainement est necessaire"
        )

    return StatePredictionResult(
        site_id=site_id,
        target_timestamp=target_timestamp,
        sensors={
            name: "on" if value else "off"
            for name, value in zip(SENSOR_COLUMNS, prediction)
        },
        model_version=metadata.trained_at,
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
