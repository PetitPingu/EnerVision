"""Use case : prédire l'état on/off de chaque capteur d'un site à partir du
dernier modèle de classification publié — à un instant donné (predict_state)
ou heure par heure sur une fenêtre (predict_state_range, pour un historique
prévisionnel du type "24 prochaines heures")."""

from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline

from application.ports import ModelStorePort, SavedModelMetadata
from infrastructure.ml.state.features import FEATURE_COLUMNS, SENSOR_COLUMNS
from infrastructure.ml.state.pipeline import predict_with_confidence


class StateModelNotLoadedError(Exception):
    """Le modèle d'état demandé est indisponible dans le store."""


class InvalidStateRangeError(Exception):
    """Le nombre d'heures demandé pour predict_state_range est invalide."""


@dataclass(frozen=True)
class SensorPrediction:
    """État prédit d'un capteur, avec la confiance du modèle (probabilité
    de la classe prédite, pas un intervalle de confiance statistique)."""

    state: str
    confidence: float


@dataclass(frozen=True)
class StatePredictionResult:
    """Résultat d'une inférence d'état sur un site et un instant cible."""

    site_id: str
    target_timestamp: datetime
    # clés = SENSOR_COLUMNS
    sensors: dict[str, SensorPrediction]
    model_version: str


@dataclass(frozen=True)
class StateRangePoint:
    """Prédiction d'état pour un instant donné, dans une série."""

    target_timestamp: datetime
    sensors: dict[str, SensorPrediction]


@dataclass(frozen=True)
class StateRangeResult:
    """Résultat d'une inférence d'état heure par heure sur une fenêtre."""

    site_id: str
    hours: int
    model_version: str
    points: tuple[StateRangePoint, ...]


def predict_state(
    model_store: ModelStorePort,
    model_name: str,
    site_id: str,
    target_timestamp: datetime,
) -> StatePredictionResult:
    """Charge le dernier modèle d'état et prédit l'état on/off de chaque
    capteur pour le site et l'instant donnés."""
    pipeline, metadata = _load_latest_model(model_store, model_name)
    x = _build_prediction_input(site_id, (target_timestamp,))
    sensors = _predict_sensors(pipeline, x, model_name)[0]

    return StatePredictionResult(
        site_id=site_id,
        target_timestamp=target_timestamp,
        sensors=sensors,
        model_version=metadata.trained_at,
    )


def predict_state_range(
    model_store: ModelStorePort,
    model_name: str,
    site_id: str,
    start_time: datetime,
    hours: int = 24,
    max_hours: int = 24 * 7,
) -> StateRangeResult:
    """Prédit l'état on/off de chaque capteur heure par heure, de
    start_time + 1h à start_time + hours (inclus) — un point par heure,
    pas de granularité minute (le modèle d'état ne l'a jamais exposée)."""
    if hours < 1 or hours > max_hours:
        raise InvalidStateRangeError(f"hours must be between 1 and {max_hours}, got {hours}")

    timestamps = tuple(start_time + timedelta(hours=offset) for offset in range(1, hours + 1))

    pipeline, metadata = _load_latest_model(model_store, model_name)
    x = _build_prediction_input(site_id, timestamps)
    sensors_per_point = _predict_sensors(pipeline, x, model_name)

    points = tuple(
        StateRangePoint(target_timestamp=ts, sensors=sensors)
        for ts, sensors in zip(timestamps, sensors_per_point, strict=True)
    )

    return StateRangeResult(
        site_id=site_id,
        hours=hours,
        model_version=metadata.trained_at,
        points=points,
    )


def _predict_sensors(
    pipeline: Pipeline,
    x: pd.DataFrame,
    model_name: str,
) -> list[dict[str, SensorPrediction]]:
    """Un dict {capteur: SensorPrediction} par ligne de x."""
    model_step = getattr(pipeline, "named_steps", {}).get("model")
    if not isinstance(model_step, MultiOutputClassifier):
        # Ancien modèle qui prédisait un état global directement (un seul
        # RandomForestClassifier) : plus exploitable tel quel, pas de
        # sortie par capteur.
        raise StateModelNotLoadedError(
            f"Le modele '{model_name}' est un ancien modele, un reentrainement est necessaire"
        )

    predictions, confidences = predict_with_confidence(pipeline, x)
    if predictions.ndim != 2 or predictions.shape[1] != len(SENSOR_COLUMNS):
        raise StateModelNotLoadedError(
            f"Le modele '{model_name}' est un ancien modele, un reentrainement est necessaire"
        )

    return [
        {
            name: SensorPrediction(
                state="on" if value else "off",
                confidence=float(confidence),
            )
            for name, value, confidence in zip(
                SENSOR_COLUMNS, prediction_row, confidence_row, strict=True
            )
        }
        for prediction_row, confidence_row in zip(predictions, confidences, strict=True)
    ]


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


def _build_prediction_input(
    site_id: str,
    target_timestamps: tuple[datetime, ...],
) -> pd.DataFrame:
    """Construit les features attendues par le pipeline sklearn."""
    return pd.DataFrame(
        [
            {
                "site_id": site_id,
                "hour": ts.hour,
                "minute": ts.minute,
            }
            for ts in target_timestamps
        ],
        columns=FEATURE_COLUMNS,
    )
