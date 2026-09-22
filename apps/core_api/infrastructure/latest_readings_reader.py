"""Dernière lecture connue par site, lue depuis Postgres (readings_curated) —
pas un relais à l'API mock.

Complète PostgresActiveAlertsReader (active_alerts_reader.py), qui ne garde
que les sites partial/degraded/critical : ici on veut TOUS les sites, y
compris ceux en "good", pour afficher un état complet (ex. la modale
Capteurs et les pastilles de la liste des sites).
"""

import logging

from application.ports import LatestReadingsPort
from db_schema.models import ReadingCurated
from domain.entities import Reading
from sqlalchemy import select

from .session import get_session

logger = logging.getLogger(__name__)


class PostgresLatestReadingsReader(LatestReadingsPort):
    """Dernière lecture connue de chaque site, toutes qualités confondues."""

    def get_latest(self) -> list[Reading]:
        try:
            with get_session() as session:
                stmt = (
                    select(ReadingCurated)
                    .distinct(ReadingCurated.site_id)
                    .order_by(ReadingCurated.site_id, ReadingCurated.timestamp.desc())
                )
                rows = session.execute(stmt).scalars().all()
        except Exception:  # noqa: BLE001 - Postgres en panne : liste vide, pas de crash
            logger.exception("Lecture du snapshot readings_curated impossible")
            return []

        return [
            Reading(
                site_id=row.site_id,
                timestamp=row.timestamp.isoformat(),
                site_type=row.site_type,
                consumption_kw=row.consumption_kw,
                consumption_kwh=row.consumption_kwh,
                voltage_v=row.voltage_v,
                current_a=row.current_a,
                power_factor=row.power_factor,
                temperature_celsius=row.temperature_celsius,
                humidity_percent=row.humidity_percent,
                null_reasons=row.null_reasons or [],
                data_quality=row.data_quality,
            )
            for row in rows
        ]
