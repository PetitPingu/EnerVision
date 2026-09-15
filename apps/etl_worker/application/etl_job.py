"""Cas d'usage : cycle ETL complet en un seul worker (docs/seq_etl.md).

Toutes les ETL_POLL_INTERVAL_SECONDS secondes : un seul appel
GET /api/v1/readings (limit=7, une lecture par site). Pour chaque
lecture : écriture brute dans le bucket raw, insertion dans
consumption_readings, et publication d'une alerte Redis si
data_quality == "critical". Chaque étape est isolée par son propre
try/except : une panne Postgres ou Redis ne doit jamais empêcher
l'écriture brute de réussir (invariant "sans perdre une seule
information", voir DATA-02 / issue #16 pour l'invariant lecture-seule
plus général).
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from ingestion import MockApiClient, MockApiError
from mockapi_client import EnergyReading

from infrastructure.alert_publisher import AlertPublisher
from infrastructure.consumption_readings_writer import ConsumptionReadingsWriter
from infrastructure.raw_writer import RawWriter

logger = logging.getLogger(__name__)

ALERT_DATA_QUALITIES = {"critical"}


class EtlJob:
    """Ingestion, transformation et détection d'alerte en un seul cycle."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        raw_writer: RawWriter | None = None,
        readings_writer: ConsumptionReadingsWriter | None = None,
        alert_publisher: AlertPublisher | None = None,
        window_seconds: int = 60,
        limit: int = 7,
    ):
        self.api_client = api_client or MockApiClient()
        self.raw_writer = raw_writer or RawWriter()
        self.readings_writer = readings_writer or ConsumptionReadingsWriter()
        self.alert_publisher = alert_publisher or AlertPublisher()
        self.window_seconds = window_seconds
        self.limit = limit

    def run(self) -> None:
        """Récupère les dernières lectures et traite chacune d'elles."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(seconds=self.window_seconds)

        try:
            readings = self.api_client.get_readings(
                start=start_time.isoformat(), end=end_time.isoformat(), limit=self.limit
            )
        except MockApiError as exc:
            self._log(site=None, status="error", data_quality=None, error=str(exc))
            return

        for reading in readings:
            self._process(reading)

    def _process(self, reading: EnergyReading) -> None:
        try:
            object_key = self.raw_writer.write(
                site_id=reading.site_id,
                timestamp=reading.timestamp,
                raw_payload=reading.raw_payload,
            )
        except Exception as exc:  # noqa: BLE001 - panne MinIO : on logge, le cycle continue
            self._log(
                reading.site_id, status="raw_write_error", data_quality=reading.data_quality, error=str(exc)
            )
            return

        inserted = None
        try:
            inserted = self.readings_writer.insert(reading)
        except Exception as exc:  # noqa: BLE001 - panne Postgres : n'empêche pas la suite
            self._log(
                reading.site_id, status="db_error", data_quality=reading.data_quality, error=str(exc)
            )

        if reading.data_quality in ALERT_DATA_QUALITIES:
            try:
                self.alert_publisher.publish(reading)
            except Exception as exc:  # noqa: BLE001 - panne Redis : n'empêche pas la suite
                self._log(
                    reading.site_id,
                    status="alert_publish_error",
                    data_quality=reading.data_quality,
                    error=str(exc),
                )

        status = "inserted" if inserted else "duplicate" if inserted is False else "written"
        self._log(reading.site_id, status=status, data_quality=reading.data_quality, object_key=object_key)

    @staticmethod
    def _log(site, status, data_quality, **extra) -> None:
        logger.info(
            json.dumps({"site": site, "status": status, "data_quality": data_quality, **extra})
        )
