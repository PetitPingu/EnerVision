"""Cas d'usage : transformation horaire des données brutes (docs/seq_etl.md).

Relit les JSON bruts du bucket raw pour la date du jour, les valide avec
les mêmes modèles Pydantic que l'ingestion (mockapi_client.EnergyReading
— aucune correction de valeur, un JSON invalide est loggé et ignoré,
jamais corrigé), et les charge dans consumption_readings.
"""

import json
import logging
from datetime import datetime, timezone

from mockapi_client import EnergyReading
from pydantic import ValidationError

from infrastructure.consumption_readings_writer import ConsumptionReadingsWriter
from infrastructure.raw_reader import RawReader

logger = logging.getLogger(__name__)


class HourlyTransformationJob:
    """Transforme les données brutes du jour en lectures structurées."""

    def __init__(
        self,
        raw_reader: RawReader | None = None,
        readings_writer: ConsumptionReadingsWriter | None = None,
    ):
        self.raw_reader = raw_reader or RawReader()
        self.readings_writer = readings_writer or ConsumptionReadingsWriter()

    def run(self) -> None:
        """Relit le bucket raw pour la date du jour et charge consumption_readings."""
        today = datetime.now(timezone.utc).date()
        payloads = self.raw_reader.read_date(today)

        inserted = duplicates = errors = 0
        for raw_payload in payloads:
            try:
                reading = EnergyReading.model_validate(json.loads(raw_payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                errors += 1
                logger.error(
                    json.dumps({"job": "transform", "status": "invalid_payload", "error": str(exc)})
                )
                continue

            if self.readings_writer.insert(reading):
                inserted += 1
            else:
                duplicates += 1

        logger.info(
            json.dumps(
                {
                    "job": "transform",
                    "date": today.isoformat(),
                    "files": len(payloads),
                    "inserted": inserted,
                    "duplicates": duplicates,
                    "errors": errors,
                }
            )
        )
