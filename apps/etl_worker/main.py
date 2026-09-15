"""Point d'entrée du worker d'ingestion (issue #19).

Interroge l'API mock toutes les ETL_POLL_INTERVAL_SECONDS secondes pour
tous les sites et alimente readings_raw (Postgres), le bucket bronze
(MinIO) et le flux Redis reading.ingested.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from application.ingest_site import SiteIngestor
from infrastructure.config import Config

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    ingestor = SiteIngestor()
    scheduler = BlockingScheduler()
    scheduler.add_job(
        ingestor.ingest_all_sites,
        "interval",
        seconds=Config.POLL_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
    )
    scheduler.start()


if __name__ == "__main__":
    main()
