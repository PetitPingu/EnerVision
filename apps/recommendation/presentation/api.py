"""API recommendation : GET /recommendations?site_id=...
(voir docs/seq_predict_call.md, "Appel au Service Recommandation").

Couche présentation : traduit la requête HTTP en cas d'usage
GenerateRecommendations et sérialise les entités du domaine en JSON. Ne
contient aucune logique métier.

Lancer en local (depuis apps/recommendation) :
    python -m uvicorn presentation.api:app --reload --port 8003

Puis ouvrir http://127.0.0.1:8003/docs pour explorer les endpoints.
"""

import os
from dataclasses import asdict

from application.generate_recommendations import GenerateRecommendations
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.prediction_client import PredictionHttpClient
from infrastructure.recommendation_repository import SqlRecommendationRepository
from infrastructure.site_repository import SqlSiteRepository

app = FastAPI(
    title="EnerVision recommendation",
    description="Génère des recommandations à partir des prédictions de consommation.",
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

generate_recommendations = GenerateRecommendations(
    prediction_api=PredictionHttpClient(),
    site_repository=SqlSiteRepository(),
    recommendation_repository=SqlRecommendationRepository(),
)


@app.get("/", tags=["Root"], summary="Root")
def root() -> dict:
    """Point d'entrée : liste les endpoints disponibles."""
    return {"endpoints": ["/docs", "/health", "/recommendations"]}


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/recommendations",
    tags=["Recommendations"],
    summary="Recommandations d'un site",
)
def list_recommendations(
    site_id: str = Query(..., description="Identifiant du site (ex: SITE001)"),
) -> list:
    """Récupère la prédiction du site, applique les règles métier, persiste
    et retourne les recommandations déclenchées (liste vide si aucune)."""
    recommendations = generate_recommendations.execute(site_id)
    if recommendations is None:
        raise HTTPException(
            status_code=404,
            detail=f"Site ou prédiction indisponible pour {site_id}",
        )
    return [asdict(r) for r in recommendations]
