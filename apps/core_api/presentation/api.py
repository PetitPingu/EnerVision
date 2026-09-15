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
