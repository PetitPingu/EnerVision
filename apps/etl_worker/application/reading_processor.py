"""Traite une lecture : écriture raw puis imputation.

Logique partagée entre le job temps réel (EtlJob) et le backfill historique.
"""

import json
import logging

from domain.imputation import ConsumptionKwhImputer
from mockapi_client import EnergyReading

from infrastructure.raw_writer import RawWriter

logger = logging.getLogger(__name__)


class ReadingProcessor:
    """Écrit la lecture brute dans MinIO et prépare la ligne curated."""

    def __init__(
        self,
        raw_writer: RawWriter | None = None,
        imputer: ConsumptionKwhImputer | None = None,
    ):
        self.raw_writer = raw_writer or RawWriter()
        self.imputer = imputer or ConsumptionKwhImputer()

    def process(self, reading: EnergyReading) -> dict | None:
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
