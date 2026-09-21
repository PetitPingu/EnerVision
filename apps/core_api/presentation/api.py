"""API core_api : relaie (proxy) l'API mock EnerVision.

Couche présentation : traduit les requêtes HTTP en appels au port
SensorApiPort et sérialise les entités du domaine en JSON. Ne contient
aucune logique métier.

Lancer en local (depuis apps/core_api) :
    python -m uvicorn presentation.api:app --reload --port 8001

Puis ouvrir http://127.0.0.1:8001/docs pour explorer les endpoints.
"""

import json
import os
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from domain.entities import AlertEvent
from infrastructure.active_alerts_reader import PostgresActiveAlertsReader
from infrastructure.api_client import ApiMockClient
from infrastructure.config import Config
from infrastructure.model_health_client import ModelHealthClient
from infrastructure.prediction_client import PredictionApiClient
from infrastructure.recommendation_client import RecommendationApiClient
from infrastructure.redis_alert_stream import RedisAlertStreamReader

# Seuils de statut du drift, cohérents avec docs/monitoring_model.md
# ("< 1 stable, 1-2 modéré, > 2 critique").
DRIFT_MODERATE_THRESHOLD = 1.0
DRIFT_CRITICAL_THRESHOLD = 2.0

alert_stream = RedisAlertStreamReader()
active_alerts_reader = PostgresActiveAlertsReader()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await alert_stream.close()


app = FastAPI(
    title="EnerVision core_api",
    description="Relaie les endpoints de l'API mock EnerVision.",
    version="1.0.0",
    lifespan=lifespan,
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
model_health_api = ModelHealthClient()


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
            "/api/v1/alerts/stream",
            "/api/v1/alerts/active",
            "/api/v1/sensors/status",
            "/api/v1/predictions/range",
            "/api/v1/recommendations",
            "/api/v1/model-health/drift",
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


@app.get(
    "/api/v1/alerts/active",
    tags=["Alerts"],
    summary="Snapshot des sites actuellement partial/degraded/critical",
)
def list_active_alerts() -> list:
    """État courant (pas le flux) : sert à amorcer la liste au chargement du
    dashboard, avant de prendre le relais avec /api/v1/alerts/stream — un
    site déjà partial/degraded/critical n'apparaît pas dans le flux tant
    qu'il ne change pas de zone (anti-flood côté etl_worker)."""
    return [_alert_event_dict(a) for a in active_alerts_reader.get_active()]


def _alert_event_dict(event: AlertEvent) -> dict:
    """dataclasses.asdict() ignore les propriétés calculées : kind est ajouté
    à la main pour que le front le reçoive sans le recalculer lui-même."""
    return {
        "event_id": event.event_id,
        "site_id": event.site_id,
        "timestamp": event.timestamp,
        "data_quality": event.data_quality,
        "null_reasons": event.null_reasons,
        "kind": event.kind,
    }


async def _sse_alert_events(request: Request, stream: RedisAlertStreamReader):
    """Générateur SSE : un événement par transition data_quality publiée sur
    Redis, un commentaire keep-alive quand rien de nouveau (évite qu'un proxy
    ou le navigateur ne coupe la connexion pendant les creux)."""
    last_id = "$"  # uniquement les événements futurs, pas de rejeu d'historique
    while not await request.is_disconnected():
        events = await stream.read_new(last_id, block_ms=Config.ALERT_STREAM_BLOCK_MS)
        if not events:
            yield ": heartbeat\n\n"
            continue
        for event in events:
            yield f"event: {event.kind}\ndata: {json.dumps(_alert_event_dict(event))}\n\n"
            last_id = event.event_id


@app.get(
    "/api/v1/alerts/stream",
    tags=["Alerts"],
    summary="Flux temps réel (SSE) des transitions data_quality",
)
async def stream_alert_events(request: Request) -> StreamingResponse:
    """Diffuse en direct les transitions data_quality publiées par etl_worker
    sur Redis Streams (alert.detected) : "alert" en entrant en degraded/
    critical, "minor_alert" en entrant en partial, "recovery" au retour à
    good."""
    return StreamingResponse(_sse_alert_events(request, alert_stream), media_type="text/event-stream")


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


@app.get(
    "/api/v1/model-health/drift",
    tags=["Model health"],
    summary="Score de drift du modèle pour un site",
)
def get_drift(
    site_id: str = Query(..., min_length=1, description="Site à surveiller, ex: SITE001"),
) -> dict:
    """Relaie ml_feature_drift_score{site=...} depuis Prometheus (voir
    docs/monitoring_model.md). Ne renvoie jamais 502 : un score absent
    (Prometheus indisponible, ou échantillon insuffisant côté
    ModelHealthJob) est un état normal (statut "unknown"), pas une panne —
    le badge de drift ne doit pas faire échouer le reste du dashboard.

    Inclut aussi mae_24h_kwh, mae_7d_kwh et mae_by_horizon : sert au
    dashboard à dessiner une marge d'erreur empirique autour de la courbe
    de prévision, qui s'élargit avec l'horizon de la prédiction
    (mae_by_horizon) plutôt qu'une largeur constante (mae_24h_kwh /
    mae_7d_kwh, utilisées en repli si une tranche d'horizon est absente,
    selon la période affichée) — pas un vrai intervalle de confiance
    statistique, voir docs/monitoring_model.md."""
    score = model_health_api.get_drift_score(site_id)
    mae_24h_kwh = model_health_api.get_mae_24h(site_id)
    mae_7d_kwh = model_health_api.get_mae_7d(site_id)
    mae_by_horizon = model_health_api.get_mae_by_horizon(site_id)

    if score is None:
        status = "unknown"
    elif score > DRIFT_CRITICAL_THRESHOLD:
        status = "critical"
    elif score > DRIFT_MODERATE_THRESHOLD:
        status = "moderate"
    else:
        status = "stable"

    return {
        "site_id": site_id,
        "drift_score": score,
        "status": status,
        "mae_24h_kwh": mae_24h_kwh,
        "mae_7d_kwh": mae_7d_kwh,
        "mae_by_horizon": mae_by_horizon,
    }
