"""Cas d'usage : ingestion périodique des dernières lectures (docs/seq_etl.md).

Un seul appel GET /api/v1/readings par cycle (limit=7 : une lecture par
site), écrite telle quelle dans le bucket raw. Aucune transformation, aucun
filtrage — y compris une lecture "critical" (tous les champs de mesure
null), écrite comme n'importe quelle autre (invariant lecture-seule de
DATA-02 / issue #16).
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from ingestion import MockApiClient, MockApiError

from infrastructure.raw_writer import RawWriter

logger = logging.getLogger(__name__)


class ReadingsIngestor:
    """Récupère les dernières lectures et les dépose dans le bucket raw."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        raw_writer: RawWriter | None = None,
        window_seconds: int = 60,
        limit: int = 7,
    ):
        self.api_client = api_client or MockApiClient()
        self.raw_writer = raw_writer or RawWriter()
        self.window_seconds = window_seconds
        self.limit = limit

    def run(self) -> None:
        """Récupère les dernières lectures et les écrit dans le bucket raw."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(seconds=self.window_seconds)

        try:
            readings = self.api_client.get_readings(
                start=start_time.isoformat(), end=end_time.isoformat(), limit=self.limit
            )
        except MockApiError as exc:
            logger.error(json.dumps({"status": "error", "error": str(exc)}))
            return

        for reading in readings:
            object_key = self.raw_writer.write(
                site_id=reading.site_id,
                timestamp=reading.timestamp,
                raw_payload=reading.raw_payload,
            )
            logger.info(
                json.dumps(
                    {
                        "site": reading.site_id,
                        "status": "written",
                        "data_quality": reading.data_quality,
                        "object_key": object_key,
                    }
                )
            )
