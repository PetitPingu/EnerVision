"""Cas d'usage : backfill historique des lectures.

Étape 1 : récupère les lectures sur une plage de dates via l'API Mock.
Les étapes suivantes (écriture raw, curation, etc.) seront ajoutées ici.
"""

import logging
from datetime import datetime, timedelta, timezone

from ingestion import MockApiClient
from mockapi_client import EnergyReading

logger = logging.getLogger(__name__)


class HistoricalBackfill:
    """Backfill historique — pour l'instant, fetch seulement."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        limit: int = 1000,
    ):
        self.api_client = api_client or MockApiClient()
        self.limit = limit

    def run(self, start: datetime, end: datetime) -> list[EnergyReading]:
        """Récupère toutes les lectures entre start et end (pagination automatique)."""
        if start >= end:
            raise ValueError(f"start ({start}) doit être strictement avant end ({end})")

        readings: list[EnergyReading] = []
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
            readings.extend(batch)
            logger.info("Page %d : %d lecture(s), total %d", page, len(batch), len(readings))

            last_ts = self._parse_timestamp(batch[-1].timestamp)
            if last_ts <= cursor:
                break

            cursor = last_ts + timedelta(microseconds=1)

        return readings

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
