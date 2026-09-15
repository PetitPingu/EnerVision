"""Cas d'usage : transformation horaire des données brutes (architecture
d'origine, voir docs/seq_etl.md).

Relit les JSON bruts déposés dans le bucket bronze durant l'heure
précédente, les valide avec les mêmes modèles Pydantic que l'ingestion
(mockapi_client.EnergyReading — aucune correction de valeur, un JSON
invalide est loggé et ignoré, jamais corrigé), et les charge dans la
table structurée enervision.readings, servie par core_api. Distinct de
l'ingestion temps réel (application/ingest_site.py), qui écrit déjà
readings_raw en direct depuis l'API mock.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from ingestion import MockApiClient, MockApiError
from mockapi_client import EnergyReading
from pydantic import ValidationError

from infrastructure.bronze_reader import BronzeReader
from infrastructure.readings_writer import ReadingsWriter
from infrastructure.sites_writer import SitesWriter

logger = logging.getLogger(__name__)


class HourlyTransformationJob:
    """Transforme les données brutes de l'heure précédente en lectures structurées."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        bronze_reader: BronzeReader | None = None,
        sites_writer: SitesWriter | None = None,
        readings_writer: ReadingsWriter | None = None,
    ):
        self.api_client = api_client or MockApiClient()
        self.bronze_reader = bronze_reader or BronzeReader()
        self.sites_writer = sites_writer or SitesWriter()
        self.readings_writer = readings_writer or ReadingsWriter()

    def run(self) -> None:
        """Synchronise les sites puis transforme l'heure précédente du bucket bronze."""
        self._sync_sites()

        previous_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        payloads = self.bronze_reader.read_hour(previous_hour)

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
                    "hour": f"{previous_hour:%Y-%m-%dT%H}",
                    "files": len(payloads),
                    "inserted": inserted,
                    "duplicates": duplicates,
                    "errors": errors,
                }
            )
        )

    def _sync_sites(self) -> None:
        try:
            sites = self.api_client.get_sites()
        except MockApiError as exc:
            logger.error(
                json.dumps({"job": "transform", "status": "sites_sync_error", "error": str(exc)})
            )
            return
        self.sites_writer.upsert_all(sites)
