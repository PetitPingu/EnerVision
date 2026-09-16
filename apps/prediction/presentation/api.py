"""API prediction : expose le modèle ML (entraînement et inférence à venir).

Couche présentation : traduit les requêtes HTTP en appels aux cas d'usage
de la couche application. Ne contient aucune logique métier.

Lancer en local (depuis apps/prediction) :
    python main.py
    # ou : python -m uvicorn presentation.api:app --reload --port 8002

Puis ouvrir http://127.0.0.1:8002/docs pour explorer les endpoints.
"""

from fastapi import FastAPI

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
        "endpoints": ["/docs", "/health"],
    }


@app.get("/health", tags=["Health"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}
