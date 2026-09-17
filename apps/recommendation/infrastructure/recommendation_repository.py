"""Implémentation SQL du RecommendationRepositoryPort (table `recommendations`)."""

import uuid

from application.ports import RecommendationRepositoryPort
from db_schema.models import Recommendation as RecommendationRow
from domain.entities import Recommendation

from .session import get_session


class SqlRecommendationRepository(RecommendationRepositoryPort):
    """Persiste les recommandations générées par le moteur de règles."""

    def save(self, recommendations: list[Recommendation]) -> None:
        if not recommendations:
            return
        rows = [
            RecommendationRow(
                id=uuid.uuid4(),
                site_id=r.site_id,
                prediction_id=r.prediction_id,
                type=r.type,
                message=r.message,
                model_version=r.model_version,
                estimated_gain_kwh=r.estimated_gain_kwh,
            )
            for r in recommendations
        ]
        with get_session() as session:
            session.add_all(rows)
            session.commit()
