"""Snapshot des sites actuellement partial/degraded/critical, lu depuis
Postgres.

Complète le flux Redis (redis_alert_stream.py) : celui-ci ne pousse que les
*transitions* (anti-flood côté etl_worker), donc un site déjà dans un état
non-good au moment où un client se connecte n'y apparaît jamais tant qu'il
ne change pas de zone. Ce reader répond à "quel est l'état actuel ?", utilisé
une fois au chargement pour amorcer la liste avant de prendre le relais avec
le flux temps réel.
"""

import logging

from application.ports import ActiveAlertsPort
from db_schema.models import ReadingCurated
from domain.entities import AlertEvent
from sqlalchemy import select

from .session import get_session

logger = logging.getLogger(__name__)

ALERT_LEVELS = ("partial", "degraded", "critical")


class PostgresActiveAlertsReader(ActiveAlertsPort):
    """Dernière lecture connue par site, filtrée sur partial/degraded/critical."""

    def get_active(self) -> list[AlertEvent]:
        try:
            with get_session() as session:
                stmt = (
                    select(ReadingCurated)
                    .distinct(ReadingCurated.site_id)
                    .order_by(ReadingCurated.site_id, ReadingCurated.timestamp.desc())
                )
                rows = session.execute(stmt).scalars().all()
        except Exception:  # noqa: BLE001 - Postgres en panne : pas de snapshot, le flux SSE prend le relais
            logger.exception("Lecture du snapshot readings_curated impossible")
            return []

        return [
            AlertEvent(
                event_id=f"snapshot:{row.site_id}:{row.timestamp.isoformat()}",
                site_id=row.site_id,
                timestamp=row.timestamp.isoformat(),
                data_quality=row.data_quality,
                null_reasons=row.null_reasons or [],
            )
            for row in rows
            if row.data_quality in ALERT_LEVELS
        ]
