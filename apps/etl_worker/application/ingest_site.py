"""Cas d'usage : ingérer la lecture temps réel d'un ou plusieurs sites.

Écriture double idempotente (readings_raw puis, seulement si nouvellement
insérée, le bucket bronze) et publication de l'événement reading.ingested.
Toute lecture — y compris une lecture "critical" où toutes les mesures
sont null — est ingérée telle quelle : ce module ne filtre, ne corrige ni
n'écarte rien (invariant lecture-seule de DATA-02 / issue #16).
"""

import json
import logging

from ingestion import MockApiClient, MockApiError

from infrastructure.minio_writer import BronzeWriter
from infrastructure.postgres_writer import ReadingsRawWriter
from infrastructure.redis_publisher import ReadingIngestedPublisher

logger = logging.getLogger(__name__)


class SiteIngestor:
    """Orchestre la lecture d'un site et son écriture dans les 3 destinations."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        bronze_writer: BronzeWriter | None = None,
        readings_writer: ReadingsRawWriter | None = None,
        event_publisher: ReadingIngestedPublisher | None = None,
    ):
        self.api_client = api_client or MockApiClient()
        self.bronze_writer = bronze_writer or BronzeWriter()
        self.readings_writer = readings_writer or ReadingsRawWriter()
        self.event_publisher = event_publisher or ReadingIngestedPublisher()

    def ingest_site(self, site_id: str) -> None:
        """Récupère la lecture courante d'un site et l'ingère."""
        try:
            reading = self.api_client.get_current(site_id)
        except MockApiError as exc:
            self._log(site_id, status="error", data_quality=None, error=str(exc))
            return

        try:
            inserted = self.readings_writer.insert(reading)
            object_key = None
            if inserted:
                object_key = self.bronze_writer.write(
                    site_id=reading.site_id,
                    timestamp=reading.timestamp,
                    raw_payload=reading.raw_payload,
                )
                self.event_publisher.publish(reading)
        except Exception as exc:  # noqa: BLE001 - panne infra : on logge, le worker continue
            self._log(site_id, status="error", data_quality=reading.data_quality, error=str(exc))
            return

        self._log(
            site_id,
            status="inserted" if inserted else "duplicate",
            data_quality=reading.data_quality,
            object_key=object_key,
        )

    def ingest_all_sites(self) -> None:
        """Ingère tous les sites retournés par l'API mock, un par un."""
        try:
            sites = self.api_client.get_sites()
        except MockApiError as exc:
            self._log(site_id=None, status="error", data_quality=None, error=str(exc))
            return

        for site in sites:
            self.ingest_site(site.site_id)

    @staticmethod
    def _log(site_id, status, data_quality, **extra) -> None:
        logger.info(
            json.dumps({"site": site_id, "status": status, "data_quality": data_quality, **extra})
        )
