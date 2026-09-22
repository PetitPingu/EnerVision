"""Tests d'intégration de SqlPowerFactorRepository contre un vrai Postgres."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from db_schema.models import ReadingCurated

from infrastructure.power_factor_repository import SqlPowerFactorRepository
from infrastructure.session import get_session

pytestmark = pytest.mark.integration


@pytest.fixture
def site_id():
    return f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _cleanup(site_id):
    yield
    with get_session() as session:
        session.query(ReadingCurated).filter(ReadingCurated.site_id == site_id).delete()
        session.commit()


def test_get_latest_power_factor_returns_most_recent_reading(site_id):
    now = datetime.now(timezone.utc)
    with get_session() as session:
        session.add_all(
            [
                ReadingCurated(site_id=site_id, timestamp=now - timedelta(minutes=5), power_factor=0.80),
                ReadingCurated(site_id=site_id, timestamp=now, power_factor=0.93),
            ]
        )
        session.commit()

    reading = SqlPowerFactorRepository().get_latest_power_factor(site_id)

    assert reading is not None
    assert reading.power_factor == 0.93


def test_get_latest_power_factor_skips_rows_with_null_power_factor(site_id):
    now = datetime.now(timezone.utc)
    with get_session() as session:
        session.add(ReadingCurated(site_id=site_id, timestamp=now, power_factor=None))
        session.commit()

    assert SqlPowerFactorRepository().get_latest_power_factor(site_id) is None


def test_get_latest_power_factor_returns_none_for_unknown_site():
    assert SqlPowerFactorRepository().get_latest_power_factor("does-not-exist") is None
