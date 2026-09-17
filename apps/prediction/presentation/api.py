"""API prediction : expose le modèle ML (entraînement et inférence à venir).

Couche présentation : traduit les requêtes HTTP en appels aux cas d'usage
de la couche application. Ne contient aucune logique métier.

Lancer en local (depuis apps/prediction) :
    python main.py
    # ou : python -m uvicorn presentation.api:app --reload --port 8002

Puis ouvrir http://127.0.0.1:8002/docs pour explorer les endpoints.
"""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query

from application.predict import ModelNotLoadedError, predict as run_predict
from infrastructure.config import Config
from infrastructure.model_store import create_model_store

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
        "endpoints": ["/docs", "/health", "/predict"],
    }


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.get("/predict", tags=["Prediction"], summary="Prédit la consommation")
def predict(
    site_id: str = Query(..., min_length=1, examples=["SITE001"]),
    timestamp: str = Query(
        ...,
        description="Horodatage cible au format ISO8601",
        examples=["2026-09-17T14:30:00Z"],
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

    return {
        "site_id": result.site_id,
        "target_timestamp": _format_iso8601(result.target_timestamp),
        "predicted_consumption_kwh": result.predicted_consumption_kwh,
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
