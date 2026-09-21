"""API prediction : expose le modèle ML (entraînement et inférence à venir).

Couche présentation : traduit les requêtes HTTP en appels aux cas d'usage
de la couche application. Ne contient aucune logique métier.

Lancer en local (depuis apps/prediction) :
    python main.py
    # ou : python -m uvicorn presentation.api:app --reload --port 8002

Puis ouvrir http://127.0.0.1:8002/docs pour explorer les endpoints.
"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query

from application.consumption.predict import (
    InvalidIntervalError,
    InvalidPredictionRangeError,
    ModelNotLoadedError,
    PredictionResult,
    predict as run_predict,
    predict_range as run_predict_range,
)
from application.state.predict_state import (
    StateModelNotLoadedError,
    predict_state as run_predict_state,
)
from infrastructure.config import Config
from infrastructure.model_store import create_model_store
from infrastructure.prediction_log_writer import PredictionLogWriter

logger = logging.getLogger(__name__)

app = FastAPI(
    title="EnerVision prediction",
    description="Service de prédiction de consommation énergétique.",
    version="0.1.0",
)


@app.get("/", tags=["Root"], summary="Root")
def root() -> dict:
    """Point d'entrée : liste les endpoints disponibles."""
    return {
        "service": "prediction",
        "endpoints": ["/docs", "/health", "/predict", "/predict/range", "/predict/state"],
    }


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.get("/predict", tags=["Prediction"], summary="Prédit la consommation")
def predict(
    site_id: str = Query(..., min_length=1, description="Site à prédire, ex: SITE001"),
    timestamp: str = Query(
        ...,
        description="Horodatage cible au format ISO8601, ex: 2026-09-17T14:30:00Z",
    ),
) -> dict:
    """Prédit la consommation (kWh) pour un site à un instant donné."""
    target_timestamp = _parse_iso8601(timestamp)
    if target_timestamp is None:
        raise HTTPException(
            status_code=422,
            detail="timestamp must be ISO8601",
        )

    try:
        result = run_predict(
            model_store=create_model_store(),
            model_name=Config.MODEL_NAME,
            site_id=site_id,
            target_timestamp=target_timestamp,
        )
    except ModelNotLoadedError:
        raise HTTPException(status_code=503, detail="model not loaded")

    _log_prediction(result)

    return {
        "site_id": result.site_id,
        "target_timestamp": _format_iso8601(result.target_timestamp),
        "predicted_consumption_kwh": result.predicted_consumption_kwh,
        "model_version": result.model_version,
    }


@app.get("/predict/range", tags=["Prediction"], summary="Prédit la consommation sur une plage")
def predict_range(
    site_id: str = Query(..., min_length=1, description="Site à prédire, ex: SITE001"),
    start_time: str = Query(
        ...,
        description="Début de la plage au format ISO8601 (inclus), ex: 2026-09-17T08:00:00Z",
    ),
    end_time: str = Query(
        ...,
        description="Fin de la plage au format ISO8601 (inclus), ex: 2026-09-17T12:00:00Z",
    ),
    interval: str = Query(
        "minute",
        description="Pas de la série retournée : 'minute' (défaut) ou 'hour'",
    ),
) -> dict:
    """Prédit la consommation (kWh) entre deux instants, minute par minute ou heure par heure."""
    parsed_start = _parse_iso8601(start_time)
    if parsed_start is None:
        raise HTTPException(status_code=422, detail="start_time must be ISO8601")

    parsed_end = _parse_iso8601(end_time)
    if parsed_end is None:
        raise HTTPException(status_code=422, detail="end_time must be ISO8601")

    try:
        result = run_predict_range(
            model_store=create_model_store(),
            model_name=Config.MODEL_NAME,
            site_id=site_id,
            start_time=parsed_start,
            end_time=parsed_end,
            interval=interval,
        )
    except InvalidIntervalError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except InvalidPredictionRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ModelNotLoadedError:
        raise HTTPException(status_code=503, detail="model not loaded")

    return {
        "site_id": result.site_id,
        "start_time": _format_iso8601(result.start_time),
        "end_time": _format_iso8601(result.end_time),
        "interval": result.interval,
        "model_version": result.model_version,
        "count": len(result.predictions),
        "predictions": [
            {
                "target_timestamp": _format_iso8601(point.target_timestamp),
                "predicted_consumption_kwh": point.predicted_consumption_kwh,
            }
            for point in result.predictions
        ],
    }


@app.get("/predict/state", tags=["Prediction"], summary="Prédit l'état futur du capteur")
def predict_state(
    site_id: str = Query(..., min_length=1, description="Site à prédire, ex: SITE001"),
    timestamp: str = Query(
        ...,
        description="Horodatage cible au format ISO8601, ex: 2026-09-17T14:30:00Z",
    ),
) -> dict:
    """Prédit l'état (data_quality : good/partial/degraded/critical) d'un
    site à un instant donné."""
    target_timestamp = _parse_iso8601(timestamp)
    if target_timestamp is None:
        raise HTTPException(
            status_code=422,
            detail="timestamp must be ISO8601",
        )

    try:
        result = run_predict_state(
            model_store=create_model_store(),
            model_name=Config.STATE_MODEL_NAME,
            site_id=site_id,
            target_timestamp=target_timestamp,
        )
    except StateModelNotLoadedError:
        raise HTTPException(status_code=503, detail="state model not loaded")

    return {
        "site_id": result.site_id,
        "target_timestamp": _format_iso8601(result.target_timestamp),
        "predicted_state": result.predicted_state,
        "model_version": result.model_version,
    }


def _parse_iso8601(value: str) -> datetime | None:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _format_iso8601(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_prediction(result: PredictionResult) -> None:
    """Écrit la prédiction dans predictions_log, sans faire échouer /predict
    si Postgres est indisponible (le rapprochement la ratera, mais la
    réponse au client reste servie)."""
    try:
        PredictionLogWriter().log(
            site_id=result.site_id,
            target_timestamp=result.target_timestamp,
            predicted_consumption_kwh=result.predicted_consumption_kwh,
            model_version=result.model_version,
        )
    except Exception:  # noqa: BLE001 - écriture d'audit best-effort
        logger.exception("predictions_log write failed for site_id=%s", result.site_id)
