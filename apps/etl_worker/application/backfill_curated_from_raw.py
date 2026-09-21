"""Backfill readings_curated depuis le bucket MinIO raw.

Relit les JSON déjà archivés dans le datalake, applique la même logique
d'imputation que EtlJob, puis upsert dans Postgres/TimescaleDB.

Usage (depuis apps/etl_worker ou conteneur etl_worker) :
    python -m application.backfill_curated_from_raw
    python -m application.backfill_curated_from_raw \\
        --prefix SITE001/ \\
        --start 2024-01-01T00:00:00 \\
        --end 2026-01-01T00:00:00

Connexion MinIO et Postgres : variables d'environnement (voir .env racine).
Idempotent : upsert sur (site_id, timestamp), relançable sans doublon.
"""

import argparse
import json
import logging
from datetime import datetime

from domain.imputation import ConsumptionKwhImputer
from infrastructure.curated_writer import CuratedWriter
from infrastructure.raw_reader import RawReader
from mockapi_client import EnergyReading

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 500


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill readings_curated depuis le bucket MinIO raw."
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Préfixe MinIO (ex. SITE001/) pour limiter à un site",
    )
    parser.add_argument("--start", help="Ignorer les lectures avant cette date (ISO 8601)")
    parser.add_argument("--end", help="Ignorer les lectures à partir de cette date (ISO 8601)")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Taille des lots upsert Postgres (défaut : {DEFAULT_BATCH_SIZE})",
    )
    return parser


def _parse_bound(value: str | None) -> datetime | None:
    if not value:
        return None
    return RawReader.parse_timestamp(value)


def _in_range(
    timestamp: str,
    start: datetime | None,
    end: datetime | None,
) -> bool:
    moment = RawReader.parse_timestamp(timestamp)
    if start is not None and moment < start:
        return False
    if end is not None and moment >= end:
        return False
    return True


def reading_to_curated_row(
    reading: EnergyReading,
    imputer: ConsumptionKwhImputer,
) -> dict:
    """Même projection que EtlJob._process, sans écriture raw ni alertes."""
    consumption_kwh, imputation_method = imputer.impute(
        reading.site_id, reading.consumption_kwh
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


class BackfillCuratedFromRawJob:
    """Relit le datalake raw et alimente readings_curated."""

    def __init__(
        self,
        raw_reader: RawReader | None = None,
        curated_writer: CuratedWriter | None = None,
        imputer: ConsumptionKwhImputer | None = None,
        prefix: str = "",
        start_time: str | None = None,
        end_time: str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.raw_reader = raw_reader or RawReader()
        self.curated_writer = curated_writer or CuratedWriter()
        self.imputer = imputer or ConsumptionKwhImputer()
        self.prefix = prefix
        self.start = _parse_bound(start_time)
        self.end = _parse_bound(end_time)
        self.batch_size = batch_size

    def run(self) -> None:
        object_keys = self.raw_reader.list_object_keys(self.prefix)
        logger.info(
            json.dumps(
                {
                    "status": "backfill_curated_started",
                    "prefix": self.prefix or None,
                    "start_time": self.start.isoformat() if self.start else None,
                    "end_time": self.end.isoformat() if self.end else None,
                    "object_count": len(object_keys),
                    "batch_size": self.batch_size,
                }
            )
        )

        batch: list[dict] = []
        written_total = 0
        skipped_total = 0
        error_total = 0

        for object_key in object_keys:
            try:
                reading = self.raw_reader.read_object(object_key)
            except Exception as exc:  # noqa: BLE001 - on logge et on continue
                error_total += 1
                logger.error(
                    json.dumps(
                        {
                            "status": "read_error",
                            "object_key": object_key,
                            "error": str(exc),
                        }
                    )
                )
                continue

            if not _in_range(reading.timestamp, self.start, self.end):
                skipped_total += 1
                continue

            batch.append(reading_to_curated_row(reading, self.imputer))

            if len(batch) >= self.batch_size:
                written_total += self._flush(batch)
                batch = []

        if batch:
            written_total += self._flush(batch)

        logger.info(
            json.dumps(
                {
                    "status": "backfill_curated_finished",
                    "written_total": written_total,
                    "skipped_total": skipped_total,
                    "error_total": error_total,
                }
            )
        )

    def _flush(self, batch: list[dict]) -> int:
        try:
            return self.curated_writer.upsert_many(batch)
        except Exception as exc:  # noqa: BLE001 - on logge et on continue le backfill
            logger.error(
                json.dumps(
                    {
                        "status": "curated_write_error",
                        "batch_size": len(batch),
                        "error": str(exc),
                    }
                )
            )
            return 0


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    BackfillCuratedFromRawJob(
        prefix=args.prefix,
        start_time=args.start,
        end_time=args.end,
        batch_size=args.batch_size,
    ).run()


if __name__ == "__main__":
    main()
