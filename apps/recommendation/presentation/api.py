"""API recommendation : GET /api/v1/recommendations?site_id=...
(voir docs/seq_predict_call.md, "Appel au Service Recommandation").

Couche présentation : traduit la requête HTTP en cas d'usage
GenerateRecommendations et sérialise les entités du domaine en JSON. Ne
contient aucune logique métier.

Lancer en local (depuis apps/recommendation) :
    python -m uvicorn presentation.api:app --reload --port 8003

Puis ouvrir http://127.0.0.1:8003/docs pour explorer les endpoints.
"""

import os

from application.generate_recommendations import GenerateRecommendations
from domain.entities import Recommendation
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.power_factor_repository import SqlPowerFactorRepository
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
    power_factor_repository=SqlPowerFactorRepository(),
    recommendation_repository=SqlRecommendationRepository(),
)


def _serialize(recommendation: Recommendation) -> dict:
    """Traduit l'entité domaine vers le contrat d'API attendu (action,
    justification, gain estimé en kWh), en référençant la prédiction et la
    version de modèle qui a produit la recommandation."""
    return {
        "site_id": recommendation.site_id,
        "action": recommendation.type,
        "justification": recommendation.message,
        "estimated_gain_kwh": recommendation.estimated_gain_kwh,
        "prediction_id": recommendation.prediction_id,
        "model_version": recommendation.model_version,
    }


@app.get("/", tags=["Root"], summary="Root")
def root() -> dict:
    """Point d'entrée : liste les endpoints disponibles."""
    return {"endpoints": ["/docs", "/health", "/api/v1/recommendations"]}


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/api/v1/recommendations",
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
    return [_serialize(r) for r in recommendations]
