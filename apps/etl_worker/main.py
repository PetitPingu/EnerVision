"""Point d'entrée du worker ETL (docs/seq_etl.md).

Un seul job planifié (APScheduler), qui tourne toutes les
ETL_POLL_INTERVAL_SECONDS secondes. Voir application/etl_job.py pour ce
qu'il fait exactement.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from application.etl_job import EtlJob
from infrastructure.config import Config

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    job = EtlJob(window_seconds=Config.POLL_INTERVAL_SECONDS)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        job.run,
        "interval",
        seconds=Config.POLL_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
    )
    scheduler.start()


if __name__ == "__main__":
    main()
