"""Use case : prédire la consommation à partir du dernier modèle publié."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from application.ports import ModelStorePort, SavedModelMetadata
from infrastructure.ml.features import FEATURE_COLUMNS


class ModelNotLoadedError(Exception):
    """Le modèle demandé est indisponible dans le store."""


@dataclass(frozen=True)
class PredictionResult:
    """Résultat d'une inférence sur un site et un instant cible."""

    site_id: str
    target_timestamp: datetime
    predicted_consumption_kwh: float
    model_version: str


def predict(
    model_store: ModelStorePort,
    model_name: str,
    site_id: str,
    target_timestamp: datetime,
) -> PredictionResult:
    """Charge le dernier modèle et prédit la consommation pour le site et l'instant donnés."""
    try:
        pipeline, metadata = model_store.load_latest(model_name)
    except Exception as exc:
        raise ModelNotLoadedError(
            f"Impossible de charger le modele '{model_name}'"
        ) from exc

    x = _build_prediction_input(site_id, target_timestamp)
    predicted_kwh = float(pipeline.predict(x)[0])

    return PredictionResult(
        site_id=site_id,
        target_timestamp=target_timestamp,
        predicted_consumption_kwh=predicted_kwh,
        model_version=metadata.trained_at,
    )


def _build_prediction_input(site_id: str, target_timestamp: datetime) -> pd.DataFrame:
    """Construit la ligne de features attendue par le pipeline sklearn."""
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
