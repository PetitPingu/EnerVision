"""Job principal du worker : ingestion + curation (docs/seq_etl.md).

Chaque cycle fait 3 choses, dans l'ordre, pour chaque lecture reçue :

1. Écrit la lecture brute dans MinIO (bucket raw), sans y toucher —
   même une lecture "critical" (tous les capteurs en panne).
2. Comble consumption_kwh si besoin (domain/imputation.py — reprend la
   dernière valeur connue du site).
3. Enregistre le résultat dans readings_curated (Postgres).
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from domain.imputation import ConsumptionKwhImputer
from ingestion import MockApiClient, MockApiError
from mockapi_client import EnergyReading

from infrastructure.curated_writer import CuratedWriter
from infrastructure.raw_writer import RawWriter

logger = logging.getLogger(__name__)


class EtlJob:
    """Récupère les dernières lectures, les dépose dans raw, et les cure."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        raw_writer: RawWriter | None = None,
        curated_writer: CuratedWriter | None = None,
        imputer: ConsumptionKwhImputer | None = None,
        window_seconds: int = 60,
        limit: int = 7,
    ):
        self.api_client = api_client or MockApiClient()
        self.raw_writer = raw_writer or RawWriter()
        self.curated_writer = curated_writer or CuratedWriter()
        self.imputer = imputer or ConsumptionKwhImputer()
        self.window_seconds = window_seconds
        self.limit = limit

    def run(self) -> None:
        """Récupère les dernières lectures, les écrit dans raw, puis cure."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(seconds=self.window_seconds)

        try:
            readings = self.api_client.get_readings(
                start=start_time.isoformat(), end=end_time.isoformat(), limit=self.limit
            )
        except MockApiError as exc:
            self._log(site=None, status="error", data_quality=None, error=str(exc))
            return

        curated_rows = [row for reading in readings if (row := self._process(reading)) is not None]

        if not curated_rows:
            return

        try:
            self.curated_writer.upsert_many(curated_rows)
        except Exception as exc:  # noqa: BLE001 - Postgres en panne : on logge et on réessaiera au prochain cycle
            self._log(site=None, status="curated_write_error", data_quality=None, error=str(exc))
            return

        self._log(site=None, status="curated", data_quality=None, written=len(curated_rows))

    def _process(self, reading: EnergyReading) -> dict | None:
        try:
            object_key = self.raw_writer.write(
                site_id=reading.site_id,
                timestamp=reading.timestamp,
                raw_payload=reading.raw_payload,
            )
        except Exception as exc:  # noqa: BLE001 - MinIO en panne : on logge et on passe à la lecture suivante
            self._log(
                reading.site_id, status="raw_write_error", data_quality=reading.data_quality, error=str(exc)
            )
            return None

        consumption_kwh, imputation_method = self.imputer.impute(
            reading.site_id, reading.consumption_kwh
        )

        self._log(
            reading.site_id,
            status="written",
            data_quality=reading.data_quality,
            object_key=object_key,
            imputation_method=imputation_method,
        )

        return {
            "site_id": reading.site_id,
            "timestamp": reading.timestamp,
            "site_type": reading.site_type,
            "consumption_kw": reading.consumption_kw,
            "consumption_kwh": consumption_kwh,
            "voltage_v": reading.voltage_v,
            "current_a": reading.current_a,
            "power_factor": reading.power_factor,
            "temperature_celsius": reading.temperature_celsius,
            "humidity_percent": reading.humidity_percent,
            "null_reasons": reading.null_reasons,
            "data_quality": reading.data_quality,
            "imputation_methods": imputation_method,
        }

    @staticmethod
    def _log(site, status, data_quality, **extra) -> None:
        logger.info(
            json.dumps({"site": site, "status": status, "data_quality": data_quality, **extra})
        )
