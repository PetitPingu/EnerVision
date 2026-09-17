"""API core_api : relaie (proxy) l'API mock EnerVision.

Couche présentation : traduit les requêtes HTTP en appels au port
SensorApiPort et sérialise les entités du domaine en JSON. Ne contient
aucune logique métier.

Lancer en local (depuis apps/core_api) :
    python -m uvicorn presentation.api:app --reload --port 8001

Puis ouvrir http://127.0.0.1:8001/docs pour explorer les endpoints.
"""

import os
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.api_client import ApiMockClient
from infrastructure.prediction_client import PredictionApiClient
from infrastructure.recommendation_client import RecommendationApiClient

app = FastAPI(
    title="EnerVision core_api",
    description="Relaie les endpoints de l'API mock EnerVision.",
    version="1.0.0",
)

_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sensor_api = ApiMockClient()
prediction_api = PredictionApiClient()
recommendation_api = RecommendationApiClient()


@app.get("/", tags=["Root"], summary="Root")
def root() -> dict:
    """Point d'entrée : liste les endpoints disponibles."""
    return {
        "endpoints": [
            "/docs",
            "/health",
            "/api/v1/sites",
            "/api/v1/sites/{site_id}/current",
            "/api/v1/readings",
            "/api/v1/alerts",
            "/api/v1/sensors/status",
            "/api/v1/predictions/range",
            "/api/v1/recommendations",
        ]
    }


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/sites", tags=["Sites"], summary="Lister tous les sites")
def list_sites() -> list:
    """Relaie la liste des sites depuis l'API mock."""
    return [asdict(site) for site in sensor_api.get_sites()]


@app.get(
    "/api/v1/sites/{site_id}/current", tags=["Readings"], summary="Lecture temps réel d'un site"
)
def get_current_reading(site_id: str) -> dict:
    """Relaie la mesure instantanée d'un site depuis l'API mock."""
    reading = sensor_api.get_current_reading(site_id)
    if reading is None:
        raise HTTPException(status_code=404, detail=f"Aucune lecture disponible pour {site_id}")
    return asdict(reading)


@app.get("/api/v1/readings", tags=["Readings"], summary="Historique des lectures")
def list_readings(
    site_id: str | None = Query(
        None, description="Filtrer par site (ex: SITE001). Si absent, retourne tous les sites."
    ),
    start_time: str | None = Query(
        None, description="Début de la période (ISO 8601). Défaut : 24h avant end_time."
    ),
    end_time: str | None = Query(
        None, description="Fin de la période (ISO 8601). Défaut : maintenant."
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Nombre maximum de résultats retournés (1-1000)."
    ),
) -> list:
    """Relaie l'historique des lectures depuis l'API mock (mêmes paramètres que la source)."""
    readings = sensor_api.get_readings(
        site_id=site_id, start_time=start_time, end_time=end_time, limit=limit
    )
    return [asdict(r) for r in readings]


@app.get("/api/v1/alerts", tags=["Alerts"], summary="Alertes actives")
def list_alerts(
    site_id: str | None = Query(None, description="Filtrer par site"),
    severity: str | None = Query(
        None, description="Filtrer par sévérité : low | medium | high | critical"
    ),
) -> list:
    """Relaie les alertes de consommation actives depuis l'API mock."""
    alerts = sensor_api.get_alerts(site_id=site_id, severity=severity)
    return [asdict(a) for a in alerts]


@app.get("/api/v1/sensors/status", tags=["Sensors"], summary="État des capteurs par site")
def sensors_status() -> dict:
    """Relaie l'état de santé des capteurs par site depuis l'API mock."""
    return sensor_api.get_sensors_status()


@app.get(
    "/api/v1/predictions/range",
    tags=["Predictions"],
    summary="Prévision de consommation sur une plage",
)
def list_predictions_range(
    site_id: str = Query(..., min_length=1, description="Site à prédire, ex: SITE001"),
    start_time: str = Query(
        ...,
        description="Début de la période au format ISO 8601, ex: 2026-09-17T08:00:00Z",
    ),
    end_time: str = Query(
        ...,
        description="Fin de la période au format ISO 8601, ex: 2026-09-17T12:00:00Z",
    ),
    interval: str = Query(
        "minute",
        description="Pas de la série retournée : 'minute' (défaut) ou 'hour'",
    ),
) -> dict:
    """Relaie GET /predict/range du service prediction."""
    result = prediction_api.get_prediction_range(
        site_id=site_id, start_time=start_time, end_time=end_time, interval=interval
    )
    if result is None:
        raise HTTPException(status_code=502, detail="Service de prédiction indisponible")
    return result


@app.get(
    "/api/v1/recommendations",
    tags=["Recommendations"],
    summary="Recommandations d'un site",
)
def list_recommendations(
    site_id: str = Query(..., min_length=1, description="Site à recommander, ex: SITE001"),
) -> list:
    """Relaie GET /api/v1/recommendations du service recommendation."""
    result = recommendation_api.get_recommendations(site_id=site_id)
    if result is None:
        raise HTTPException(status_code=502, detail="Service de recommandation indisponible")
    return result
