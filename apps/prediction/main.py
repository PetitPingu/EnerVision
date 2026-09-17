"""Point d'entrée du service Prediction.

Composition root : câble l'entraînement planifié (APScheduler) et sert
l'API. Le modèle n'est pas chargé en mémoire ici - predict.py le recharge
à chaque appel via model_store.load_latest(), donc une promotion par
retrain_if_better() est visible immédiatement, sans redémarrage.

Lancer en local (depuis apps/prediction) :
    python main.py
"""

import logging

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from application.retrain_if_better import retrain_if_better
from infrastructure.config import Config
from infrastructure.model_store import create_model_store
from infrastructure.training_data import create_training_data_reader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _run_scheduled_retrain() -> None:
    """Job APScheduler : ré-entraîne et ne promeut que si meilleur (voir
    application.retrain_if_better)."""
    try:
        result = retrain_if_better(
            data_reader=create_training_data_reader(),
            model_store=create_model_store(),
            model_name=Config.MODEL_NAME,
        )
    except Exception:
        logger.exception("Echec du reentrainement planifie")
        return

    if result.promoted:
        logger.info(
            "Nouveau modele promu : mae=%.2f (ancien champion: %s)",
            result.metadata.mae,
            f"{result.champion_mae:.2f}" if result.champion_mae is not None else "aucun",
        )
    else:
        logger.info(
            "Candidat ecarte : mae=%.2f >= champion actuel mae=%.2f",
            result.metadata.mae,
            result.champion_mae,
        )


def _start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_scheduled_retrain,
        "interval",
        hours=Config.RETRAIN_INTERVAL_HOURS,
        id="scheduled_retrain",
    )
    scheduler.start()
    return scheduler


def main() -> None:
    _start_scheduler()
    uvicorn.run(
        "presentation.api:app",
        host="0.0.0.0",
        port=Config.PORT,
        reload=Config.RELOAD,
    )


if __name__ == "__main__":
    main()
