"""Point d'entrée du worker d'ingestion (issue #19).

Deux jobs planifiés (APScheduler) :
- Ingestion temps réel, toutes les ETL_POLL_INTERVAL_SECONDS secondes :
  interroge l'API mock pour tous les sites et alimente readings_raw
  (Postgres), le bucket bronze (MinIO) et le flux Redis reading.ingested.
- Transformation horaire (architecture d'origine, voir docs/seq_etl.md) :
  relit les JSON bruts de l'heure précédente dans bronze, les valide et
  les charge dans enervision.readings (table structurée servie par
  core_api).
"""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from application.ingest_site import SiteIngestor
from application.transform_readings import HourlyTransformationJob
from infrastructure.config import Config

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    ingestor = SiteIngestor()
    transformation_job = HourlyTransformationJob()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        ingestor.ingest_all_sites,
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
