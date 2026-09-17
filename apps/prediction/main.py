"""Point d'entrée du service Prediction.

Composition root : c'est ici que seront câblés l'entraînement planifié
(APScheduler) et le chargement du modèle en mémoire au démarrage.

Lancer en local (depuis apps/prediction) :
    python main.py
"""

import logging

import uvicorn

from infrastructure.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    uvicorn.run(
        "presentation.api:app",
        host="0.0.0.0",
        port=Config.PORT,
        reload=Config.RELOAD,
    )


if __name__ == "__main__":
    main()
