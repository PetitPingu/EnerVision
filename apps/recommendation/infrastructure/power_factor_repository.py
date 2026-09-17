"""Implémentation SQL du PowerFactorRepositoryPort (table `readings_curated`).

power_factor n'est pas prédit par le service Prediction : c'est une mesure
réelle, on lit donc la dernière valeur connue plutôt que de la déduire
d'une prédiction.
"""

from application.ports import PowerFactorRepositoryPort
from db_schema.models import ReadingCurated
from domain.entities import PowerFactorReading
from sqlalchemy import select

from .session import get_session


class SqlPowerFactorRepository(PowerFactorRepositoryPort):
    """Lit le dernier facteur de puissance connu d'un site."""

    def get_latest_power_factor(self, site_id: str) -> PowerFactorReading | None:
        statement = (
            select(ReadingCurated)
            .where(
                ReadingCurated.site_id == site_id,
                ReadingCurated.power_factor.is_not(None),
            )
            .order_by(ReadingCurated.timestamp.desc())
            .limit(1)
        )
        with get_session() as session:
            row = session.execute(statement).scalar_one_or_none()
        if row is None:
            return None
        return PowerFactorReading(site_id=site_id, power_factor=row.power_factor)
