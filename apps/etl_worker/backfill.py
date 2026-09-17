"""Point d'entrée CLI du backfill historique.

Usage (depuis apps/etl_worker) :
    python backfill.py --start 2024-01-01 --end 2026-09-17

Depuis Docker :
    docker compose run --rm etl_worker python backfill.py --start 2024-01-01

Variables d'environnement : voir .env à la racine du monorepo
(API mock, MinIO, DATABASE_URL).
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from application.historical_backfill import HistoricalBackfill

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def parse_datetime(value: str) -> datetime:
    """Parse une date ISO (YYYY-MM-DD ou datetime complet) en UTC."""
    if len(value) == 10:
        parsed = datetime.fromisoformat(value)
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill historique des lectures EnerVision.")
    parser.add_argument(
        "--start",
        required=True,
        help="Date de début (YYYY-MM-DD ou ISO 8601, ex. 2024-01-01).",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Date de fin (défaut : maintenant, UTC).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    start = parse_datetime(args.start)
    end = parse_datetime(args.end) if args.end else datetime.now(timezone.utc)

    logger.info("Backfill de %s à %s", start.isoformat(), end.isoformat())

    try:
        stats = HistoricalBackfill().run(start, end)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    logger.info(
        "Terminé : %d fetchée(s), %d curée(s), %d ignorée(s)",
        stats["fetched"],
        stats["curated"],
        stats["skipped"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
