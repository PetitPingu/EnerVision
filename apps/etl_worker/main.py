"""Point d'entrée du worker ETL (docs/seq_etl.md, docs/monitoring_model.md).

Deux jobs planifiés (APScheduler) :
- EtlJob, toutes les ETL_POLL_INTERVAL_SECONDS secondes (voir
  application/etl_job.py) ;
- ModelHealthJob, toutes les MODEL_HEALTH_INTERVAL_SECONDS secondes
  (rapprochement MAE 24h + drift, voir application/model_health_job.py),
  exposé en Prometheus sur ETL_METRICS_PORT.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from application.etl_job import EtlJob
from application.model_health_job import ModelHealthJob
from infrastructure.config import Config
from infrastructure.model_health_metrics import start_metrics_server

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    start_metrics_server(Config.METRICS_PORT)

    etl_job = EtlJob(window_seconds=Config.POLL_INTERVAL_SECONDS)
    model_health_job = ModelHealthJob()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        etl_job.run,
        "interval",
        seconds=Config.POLL_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        model_health_job.run,
        "interval",
        seconds=Config.MODEL_HEALTH_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
    )
    scheduler.start()


if __name__ == "__main__":
    main()
