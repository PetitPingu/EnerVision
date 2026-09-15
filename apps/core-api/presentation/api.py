"""API core-api : relaie (proxy) l'API mock EnerVision.

Couche présentation : traduit les requêtes HTTP en appels au port
SensorApiPort et sérialise les entités du domaine en JSON. Ne contient
aucune logique métier.

Lancer en local (depuis apps/core-api) :
    python -m uvicorn presentation.api:app --reload --port 8001

Puis ouvrir http://127.0.0.1:8001/docs pour explorer les endpoints.
"""

from dataclasses import asdict

from fastapi import FastAPI, Query
from infrastructure.api_client import ApiMockClient

app = FastAPI(
    title="EnerVision core-api",
    description="Relaie les endpoints de l'API mock EnerVision.",
    version="1.0.0",
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
            "/api/v1/readings",
        ]
    }


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/sites", tags=["Sites"], summary="Lister tous les sites")
def list_sites() -> list:
    """Relaie la liste des sites depuis l'API mock."""
    return [asdict(site) for site in sensor_api.get_sites()]


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
