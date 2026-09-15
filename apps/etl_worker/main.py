"""Point d'entrée du worker ETL (docs/seq_etl.md).

Deux jobs planifiés (APScheduler) :
- Ingestion, toutes les ETL_POLL_INTERVAL_SECONDS secondes : récupère les
  dernières lectures (GET /api/v1/readings) et les dépose brutes dans le
  bucket raw de MinIO.
- Transformation, toutes les heures : relit le bucket raw pour la date du
  jour, valide chaque JSON et le charge dans consumption_readings.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from application.ingest_readings import ReadingsIngestor
from application.transform_readings import HourlyTransformationJob
from infrastructure.config import Config

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    ingestor = ReadingsIngestor(window_seconds=Config.POLL_INTERVAL_SECONDS)
    transformation_job = HourlyTransformationJob()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        ingestor.run,
        "interval",
        seconds=Config.POLL_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        transformation_job.run,
        "cron",
        minute=0,
        next_run_time=datetime.now(),
    )
    scheduler.start()


if __name__ == "__main__":
    main()
