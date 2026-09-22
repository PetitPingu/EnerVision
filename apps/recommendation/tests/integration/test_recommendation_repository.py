"""Tests d'intégration de SqlRecommendationRepository contre un vrai Postgres."""

import uuid

import pytest
from db_schema.models import Recommendation as RecommendationRow
from db_schema.models import Site as SiteRow

from domain.entities import Recommendation
from infrastructure.recommendation_repository import SqlRecommendationRepository
from infrastructure.session import get_session

pytestmark = pytest.mark.integration


@pytest.fixture
def site_id():
    sid = f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}"
    with get_session() as session:
        session.add(SiteRow(site_id=sid, site_name="Usine test", capacity_kw=100.0))
        session.commit()

    yield sid

    with get_session() as session:
        session.query(RecommendationRow).filter(RecommendationRow.site_id == sid).delete()
        session.query(SiteRow).filter(SiteRow.site_id == sid).delete()
        session.commit()


def test_save_persists_recommendations(site_id):
    repo = SqlRecommendationRepository()
    recommendations = [
        Recommendation(
            site_id=site_id,
            type="peak_shaving",
            message="Décaler la charge hors pointe",
            prediction_id=None,
            model_version="v1",
            estimated_gain_kwh=12.5,
        )
    ]

    repo.save(recommendations)

    with get_session() as session:
        rows = session.query(RecommendationRow).filter(RecommendationRow.site_id == site_id).all()
    assert len(rows) == 1
    assert rows[0].message == "Décaler la charge hors pointe"
    assert rows[0].estimated_gain_kwh == 12.5
    assert rows[0].model_version == "v1"


def test_save_with_empty_list_does_not_touch_the_database(site_id):
    repo = SqlRecommendationRepository()

    repo.save([])

    with get_session() as session:
        count = (
            session.query(RecommendationRow).filter(RecommendationRow.site_id == site_id).count()
        )
    assert count == 0
