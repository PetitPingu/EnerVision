"""Backfill historique des lectures vers MinIO (bucket raw).

Récupère les lectures par fenêtre d'une heure (tous sites, sans site_id,
limit=420 = 60 minutes × 7 sites) et les dépose dans MinIO via RawWriter.

Usage (depuis apps/etl_worker) :
    python -m application.backfill_readings \\
        --start 2024-01-01T00:00:00 \\
        --end 2026-01-01T00:00:00 \\
        --limit 420

Connexion API et MinIO : variables d'environnement (voir .env racine).
"""

import argparse
import json
import logging
from datetime import datetime, timedelta

from ingestion import MockApiClient, MockApiError
from infrastructure.raw_writer import RawWriter

logger = logging.getLogger(__name__)

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_HOURLY_LIMIT = 420


def iter_hourly_windows(start: datetime, end: datetime):
    """Découpe [start, end) en fenêtres d'une heure."""
    current = start
    while current < end:
        window_end = min(current + timedelta(hours=1), end)
        yield current, window_end
        current = window_end


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _ensure_bucket(raw_writer: RawWriter) -> None:
    client = raw_writer._client
    bucket = raw_writer._bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info(json.dumps({"status": "bucket_created", "bucket": bucket}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill des lectures API vers MinIO (bucket raw).")
    parser.add_argument("--start", required=True, help="Début de la période (ex. 2024-01-01T00:00:00)")
    parser.add_argument("--end", required=True, help="Fin de la période (ex. 2026-01-01T00:00:00)")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_HOURLY_LIMIT,
        help=f"Limite par fenêtre horaire (défaut : {DEFAULT_HOURLY_LIMIT})",
    )
    return parser


class BackfillReadingsJob:
    """Récupère l'historique des lectures par heure et les écrit dans raw."""

    def __init__(
        self,
        api_client: MockApiClient | None = None,
        raw_writer: RawWriter | None = None,
        start_time: str = "",
        end_time: str = "",
        hourly_limit: int = DEFAULT_HOURLY_LIMIT,
    ):
        self.api_client = api_client or MockApiClient()
        self.raw_writer = raw_writer or RawWriter()
        self.start_time = start_time
        self.end_time = end_time
        self.hourly_limit = hourly_limit

    def run(self) -> None:
        start = _parse_datetime(self.start_time)
        end = _parse_datetime(self.end_time)
        windows = list(iter_hourly_windows(start, end))
        total_windows = len(windows)

        _ensure_bucket(self.raw_writer)

        logger.info(
            json.dumps(
                {
                    "status": "backfill_started",
                    "start_time": self.start_time,
                    "end_time": self.end_time,
                    "hourly_limit": self.hourly_limit,
                    "total_windows": total_windows,
                }
            )
        )

        written_total = 0
        error_total = 0

        for index, (window_start, window_end) in enumerate(windows, start=1):
            start_param = window_start.strftime(TIMESTAMP_FORMAT)
            end_param = window_end.strftime(TIMESTAMP_FORMAT)

            try:
                readings = self.api_client.get_readings(
                    start=start_param,
                    end=end_param,
                    limit=self.hourly_limit,
                )
            except MockApiError as exc:
                error_total += 1
                logger.error(
                    json.dumps(
                        {
                            "status": "fetch_error",
                            "window": index,
                            "total_windows": total_windows,
                            "start_time": start_param,
                            "end_time": end_param,
                            "error": str(exc),
                        }
                    )
                )
                continue

            window_written = 0
            for reading in readings:
                try:
                    self.raw_writer.write(
                        site_id=reading.site_id,
                        timestamp=reading.timestamp,
                        raw_payload=reading.raw_payload,
                    )
                except Exception as exc:  # noqa: BLE001 - on logge et on continue le backfill
                    error_total += 1
                    logger.error(
                        json.dumps(
                            {
                                "status": "write_error",
                                "site": reading.site_id,
                                "timestamp": reading.timestamp,
                                "error": str(exc),
                            }
                        )
                    )
                    continue

                window_written += 1
                written_total += 1

            logger.info(
                json.dumps(
                    {
                        "status": "window_done",
                        "window": index,
                        "total_windows": total_windows,
                        "start_time": start_param,
                        "end_time": end_param,
                        "fetched": len(readings),
                        "written": window_written,
                    }
                )
            )

        logger.info(
            json.dumps(
                {
                    "status": "backfill_finished",
                    "total_windows": total_windows,
                    "written_total": written_total,
                    "error_total": error_total,
                }
            )
        )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = build_parser().parse_args(argv)
    BackfillReadingsJob(
        start_time=args.start,
        end_time=args.end,
        hourly_limit=args.limit,
    ).run()


if __name__ == "__main__":
    main()
