"""Point d'entrée du service Prediction.

Composition root : câble l'entraînement planifié (APScheduler) et sert
l'API. Les modèles ne sont pas mis en cache ici - predict.py/predict_state.py
les rechargent à chaque appel via model_store.load_latest(), donc une
promotion par retrain_if_better()/retrain_state_if_better() est visible
immédiatement, sans redémarrage. Au démarrage, on tente quand même un
load_latest() de chaque modèle "Production" pour échouer vite (log d'alerte)
si un modèle n'a encore jamais été entraîné/promu.

Lancer en local (depuis apps/prediction) :
    python main.py
"""

import logging

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from application.consumption.retrain_if_better import retrain_if_better
from application.state.retrain_state_if_better import retrain_state_if_better
from infrastructure.config import Config
from infrastructure.model_store import create_model_store
from infrastructure.training_data import (
    create_state_training_data_reader,
    create_training_data_reader,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _run_scheduled_retrain() -> None:
    """Job APScheduler : ré-entraîne et ne promeut que si meilleur (voir
    application.consumption.retrain_if_better)."""
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


def _run_scheduled_retrain_state() -> None:
    """Job APScheduler : ré-entraîne le modele d'etat et ne le promeut que
    si meilleur (voir application.state.retrain_state_if_better)."""
    try:
        result = retrain_state_if_better(
            data_reader=create_state_training_data_reader(),
            model_store=create_model_store(),
            model_name=Config.STATE_MODEL_NAME,
        )
    except Exception:
        logger.exception("Echec du reentrainement planifie (etat)")
        return

    if result.promoted:
        logger.info(
            "Nouveau modele d'etat promu : accuracy=%.2f (ancien champion: %s)",
            result.metadata.metrics["accuracy"],
            f"{result.champion_accuracy:.2f}" if result.champion_accuracy is not None else "aucun",
        )
    else:
        logger.info(
            "Candidat d'etat ecarte : accuracy=%.2f <= champion actuel accuracy=%.2f",
            result.metadata.metrics["accuracy"],
            result.champion_accuracy,
        )


def _start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_scheduled_retrain,
        "interval",
        hours=Config.RETRAIN_INTERVAL_HOURS,
        id="scheduled_retrain",
    )
    scheduler.add_job(
        _run_scheduled_retrain_state,
        "interval",
        hours=Config.RETRAIN_INTERVAL_HOURS,
        id="scheduled_retrain_state",
    )
    scheduler.start()
    return scheduler


def _check_models_loaded_at_startup() -> None:
    """Vérifie que chaque modèle "Production" est chargeable au démarrage -
    échoue vite (log d'alerte) plutôt que de laisser l'API répondre 503 sans
    explication au premier appel."""
    model_store = create_model_store()

    for label, model_name in (
        ("consommation", Config.MODEL_NAME),
        ("etat", Config.STATE_MODEL_NAME),
    ):
        try:
            _, metadata = model_store.load_latest(model_name)
            logger.info(
                "Modele %s (%s) charge au demarrage : version=%s",
                label,
                model_name,
                metadata.trained_at,
            )
        except Exception:
            logger.warning(
                "Modele %s (%s) indisponible au demarrage - "
                "aucun entrainement promu pour l'instant",
                label,
                model_name,
            )


def main() -> None:
    _check_models_loaded_at_startup()
    _start_scheduler()
    uvicorn.run(
        "presentation.api:app",
        host="0.0.0.0",
        port=Config.PORT,
        reload=Config.RELOAD,
    )


if __name__ == "__main__":
    main()
