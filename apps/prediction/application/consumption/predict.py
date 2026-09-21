"""Use case : prédire la consommation à partir du dernier modèle publié."""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from sklearn.pipeline import Pipeline

from application.ports import ModelStorePort, SavedModelMetadata
from infrastructure.config import Config
from infrastructure.ml.consumption.features import FEATURE_COLUMNS


class ModelNotLoadedError(Exception):
    """Le modèle demandé est indisponible dans le store."""


class InvalidPredictionRangeError(Exception):
    """La plage de prédiction demandée est invalide ou dépasse la limite autorisée."""


class InvalidIntervalError(Exception):
    """L'intervalle demandé n'est pas supporté (minute | hour)."""


_INTERVALS: dict[str, tuple[str, int]] = {
    # interval -> (fréquence pandas, minutes par point)
    "minute": ("min", 1),
    "hour": ("h", 60),
}


@dataclass(frozen=True)
class PredictionResult:
    """Résultat d'une inférence sur un site et un instant cible."""

    site_id: str
    target_timestamp: datetime
    predicted_consumption_kwh: float
    model_version: str


@dataclass(frozen=True)
class PredictionPoint:
    """Prédiction pour un instant donné."""

    target_timestamp: datetime
    predicted_consumption_kwh: float


@dataclass(frozen=True)
class PredictionRangeResult:
    """Résultat d'une inférence sur une plage temporelle, à l'intervalle demandé."""

    site_id: str
    start_time: datetime
    end_time: datetime
    interval: str
    model_version: str
    predictions: tuple[PredictionPoint, ...]


def predict(
    model_store: ModelStorePort,
    model_name: str,
    site_id: str,
    target_timestamp: datetime,
) -> PredictionResult:
    """Charge le dernier modèle et prédit la consommation pour le site et l'instant donnés."""
    pipeline, metadata = _load_latest_model(model_store, model_name)
    x = _build_prediction_input(site_id, (target_timestamp,))
    predicted_kwh = float(pipeline.predict(x)[0])

    return PredictionResult(
        site_id=site_id,
        target_timestamp=target_timestamp,
        predicted_consumption_kwh=predicted_kwh,
        model_version=metadata.trained_at,
    )


def predict_range(
    model_store: ModelStorePort,
    model_name: str,
    site_id: str,
    start_time: datetime,
    end_time: datetime,
    interval: str = "minute",
    max_minutes: int = Config.MAX_PREDICTION_RANGE_MINUTES,
) -> PredictionRangeResult:
    """Prédit la consommation entre start_time et end_time (inclus).

    `interval` contrôle le pas de la série retournée : "minute" (défaut,
    comportement historique) ou "hour" pour une agrégation horaire — utile
    pour les vues longue durée (ex. semaine), qui n'ont pas besoin de la
    granularité minute et évitent ainsi de faire tourner le modèle sur des
    milliers de points inutiles.
    """
    timestamps = _generate_timestamp_range(start_time, end_time, interval, max_minutes)
    pipeline, metadata = _load_latest_model(model_store, model_name)
    x = _build_prediction_input(site_id, timestamps)
    predicted_values = pipeline.predict(x)

    predictions = tuple(
        PredictionPoint(
            target_timestamp=ts.to_pydatetime().astimezone(start_time.tzinfo),
            predicted_consumption_kwh=float(value),
        )
        for ts, value in zip(timestamps, predicted_values, strict=True)
    )

    return PredictionRangeResult(
        site_id=site_id,
        start_time=start_time,
        end_time=end_time,
        interval=interval,
        model_version=metadata.trained_at,
        predictions=predictions,
    )


def _load_latest_model(
    model_store: ModelStorePort,
    model_name: str,
) -> tuple[Pipeline, SavedModelMetadata]:
    try:
        return model_store.load_latest(model_name)
    except Exception as exc:
        raise ModelNotLoadedError(
            f"Impossible de charger le modele '{model_name}'"
        ) from exc


def _generate_timestamp_range(
    start_time: datetime,
    end_time: datetime,
    interval: str,
    max_minutes: int,
) -> pd.DatetimeIndex:
    if start_time > end_time:
        raise InvalidPredictionRangeError("start_time must be before end_time")

    if interval not in _INTERVALS:
        raise InvalidIntervalError(
            f"interval must be one of {sorted(_INTERVALS)}, got '{interval}'"
        )
    freq, minutes_per_point = _INTERVALS[interval]
    max_points = max_minutes // minutes_per_point

    timestamps = pd.date_range(
        start=start_time,
        end=end_time,
        freq=freq,
        inclusive="both",
    )
    if len(timestamps) > max_points:
        raise InvalidPredictionRangeError(
            f"range exceeds maximum of {max_points} points at interval '{interval}'"
        )

    return timestamps


def _build_prediction_input(
    site_id: str,
    target_timestamps: tuple[datetime, ...] | pd.DatetimeIndex,
) -> pd.DataFrame:
    """Construit les features attendues par le pipeline sklearn."""
    if isinstance(target_timestamps, pd.DatetimeIndex):
        timestamps = target_timestamps.to_pydatetime()
    else:
        timestamps = target_timestamps

    return pd.DataFrame(
        [
            {
                "site_id": site_id,
                "hour": ts.hour,
                "minute": ts.minute,
            }
            for ts in timestamps
        ],
        columns=FEATURE_COLUMNS,
    )
