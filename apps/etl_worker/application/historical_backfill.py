"""Cas d'usage : backfill historique des lectures.

1. Un appel API par jour calendaire (start/end en date, limit=1000).
2. Pour chaque lecture : écriture raw (MinIO) + imputation consumption_kwh.
3. Upsert des lignes curées dans readings_curated (Postgres).
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone

from domain.imputation import ConsumptionKwhImputer
from ingestion import MockApiClient

from application.reading_processor import ReadingProcessor
from infrastructure.curated_writer import CuratedWriter
from infrastructure.raw_writer import RawWriter

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 1000


class HistoricalBackfill:
    """Backfill historique : exactement un fetch par jour."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        raw_writer: RawWriter | None = None,
        curated_writer: CuratedWriter | None = None,
        imputer: ConsumptionKwhImputer | None = None,
        limit: int = DEFAULT_LIMIT,
    ):
        self.api_client = api_client or MockApiClient()
        self.raw_writer = raw_writer or RawWriter()
        self.curated_writer = curated_writer or CuratedWriter()
        self.imputer = imputer or ConsumptionKwhImputer()
        self.processor = ReadingProcessor(raw_writer=self.raw_writer, imputer=self.imputer)
        self.limit = limit

    def run(self, start: date, end: date) -> dict:
        """Backfill du jour start au jour end (inclus). Un appel API par jour."""
        if start > end:
            raise ValueError(f"start ({start}) doit être avant ou égal à end ({end})")

        stats = {"fetched": 0, "curated": 0, "skipped": 0, "days_done": 0}
        total_days = (end - start).days + 1
        current = start
        day_index = 0

        while current <= end:
            day_index += 1
            day_start = datetime(current.year, current.month, current.day, tzinfo=timezone.utc)
            day_end = day_start + timedelta(days=1)

            readings = self.api_client.get_readings(
                start=day_start.isoformat(),
                end=day_end.isoformat(),
                limit=self.limit,
            )

            stats["fetched"] += len(readings)
            curated_rows = [
                row for reading in readings if (row := self.processor.process(reading)) is not None
            ]
            stats["skipped"] += len(readings) - len(curated_rows)

            if curated_rows:
                try:
                    self.curated_writer.upsert_many(curated_rows)
                except Exception as exc:  # noqa: BLE001
                    self._log(status="curated_write_error", error=str(exc), day=current.isoformat())
                    return stats

                stats["curated"] += len(curated_rows)

            stats["days_done"] += 1
            logger.info(
                "Jour %d/%d (%s) : %d fetchée(s), %d curée(s), total %d",
                day_index,
                total_days,
                current.isoformat(),
                len(readings),
                len(curated_rows),
                stats["curated"],
            )

            current += timedelta(days=1)

        return stats

    @staticmethod
    def _log(**extra) -> None:
        logger.info(json.dumps(extra))
