"""Point d'entrée CLI du backfill historique.

Usage (depuis apps/etl_worker) :
    python backfill.py --start 2024-05-28 --end 2026-09-15
    python backfill.py --start 2026-09-16 --end 2026-09-17

Un appel API par jour calendaire (limit=1000). Les deux dates sont incluses.

Depuis Docker :
    docker compose run --rm etl_worker python backfill.py --start 2024-01-01 --end 2024-01-31

Variables d'environnement : voir .env à la racine du monorepo
(API mock, MinIO, DATABASE_URL).
"""

import argparse
import logging
import sys
from datetime import date, datetime, timezone

from application.historical_backfill import HistoricalBackfill

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def parse_date(value: str) -> date:
    """Parse une date YYYY-MM-DD."""
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill historique des lectures EnerVision.")
    parser.add_argument(
        "--start",
        required=True,
        help="Date de début inclusive (YYYY-MM-DD, ex. 2024-05-28).",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Date de fin inclusive (YYYY-MM-DD). Défaut : aujourd'hui (UTC).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    start = parse_date(args.start)
    end = parse_date(args.end) if args.end else datetime.now(timezone.utc).date()

    total_days = (end - start).days + 1
    logger.info(
        "Backfill du %s au %s (%d jour(s), 1 appel API/jour, limit=1000)",
        start.isoformat(),
        end.isoformat(),
        total_days,
    )

    try:
        stats = HistoricalBackfill().run(start, end)
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    logger.info(
        "Terminé (%d/%d jour(s)) : %d fetchée(s), %d curée(s), %d ignorée(s)",
        stats["days_done"],
        total_days,
        stats["fetched"],
        stats["curated"],
        stats["skipped"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
