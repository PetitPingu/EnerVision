"""Cas d'usage : backfill historique des lectures.

1. Récupère les lectures sur une plage de dates via l'API Mock (pagination).
2. Pour chaque lecture : écriture raw (MinIO) + imputation consumption_kwh.
3. Upsert des lignes curées dans readings_curated (Postgres), page par page.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from domain.imputation import ConsumptionKwhImputer
from ingestion import MockApiClient

from application.reading_processor import ReadingProcessor
from infrastructure.curated_writer import CuratedWriter
from infrastructure.raw_writer import RawWriter

logger = logging.getLogger(__name__)


class HistoricalBackfill:
    """Backfill historique : fetch paginé, traitement et écriture curated."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        raw_writer: RawWriter | None = None,
        curated_writer: CuratedWriter | None = None,
        imputer: ConsumptionKwhImputer | None = None,
        limit: int = 1000,
    ):
        self.api_client = api_client or MockApiClient()
        self.raw_writer = raw_writer or RawWriter()
        self.curated_writer = curated_writer or CuratedWriter()
        self.imputer = imputer or ConsumptionKwhImputer()
        self.processor = ReadingProcessor(raw_writer=self.raw_writer, imputer=self.imputer)
        self.limit = limit

    def run(self, start: datetime, end: datetime) -> dict:
        """Backfill entre start et end. Retourne un résumé {fetched, curated, skipped}."""
        if start >= end:
            raise ValueError(f"start ({start}) doit être strictement avant end ({end})")

        stats = {"fetched": 0, "curated": 0, "skipped": 0}
        cursor = start
        page = 0

        while cursor < end:
            batch = self.api_client.get_readings(
                start=cursor.isoformat(),
                end=end.isoformat(),
                limit=self.limit,
            )
            if not batch:
                break

            page += 1
            stats["fetched"] += len(batch)
            curated_rows = [
                row for reading in batch if (row := self.processor.process(reading)) is not None
            ]
            stats["skipped"] += len(batch) - len(curated_rows)

            if curated_rows:
                try:
                    self.curated_writer.upsert_many(curated_rows)
                except Exception as exc:  # noqa: BLE001 - Postgres en panne : on logge et on arrête le backfill
                    self._log(status="curated_write_error", error=str(exc), page=page)
                    return stats

                stats["curated"] += len(curated_rows)

            logger.info(
                "Page %d : %d fetchée(s), %d curée(s), %d ignorée(s), total %d",
                page,
                len(batch),
                len(curated_rows),
                len(batch) - len(curated_rows),
                stats["curated"],
            )

            last_ts = self._parse_timestamp(batch[-1].timestamp)
            if last_ts <= cursor:
                break

            cursor = last_ts + timedelta(microseconds=1)

        return stats

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _log(**extra) -> None:
        logger.info(json.dumps(extra))
