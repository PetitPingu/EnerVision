"""Tests d'intégration de PostgresTrainingDataReader contre un vrai Postgres."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from db_schema.models import ReadingCurated

from infrastructure.config import Config
from infrastructure.training_data.consumption.postgres_reader import PostgresTrainingDataReader

pytestmark = pytest.mark.integration


@pytest.fixture
def site_id():
    return f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _cleanup(db_engine, site_id):
    yield
    with db_engine.begin() as conn:
        conn.execute(ReadingCurated.__table__.delete().where(ReadingCurated.site_id == site_id))


def _insert_two_rows(db_engine, site_id: str) -> None:
    now = datetime.now(timezone.utc)
    with db_engine.begin() as conn:
        conn.execute(
            ReadingCurated.__table__.insert(),
            [
                {"site_id": site_id, "timestamp": now, "consumption_kwh": 5.0},
                {"site_id": site_id, "timestamp": now + timedelta(minutes=1), "consumption_kwh": None},
            ],
        )


def test_fetch_training_data_excludes_rows_with_null_consumption_kwh(db_engine, site_id):
    _insert_two_rows(db_engine, site_id)

    reader = PostgresTrainingDataReader(Config.DATABASE_URL, engine=db_engine)
    df = reader.fetch_training_data()

    matching = df[df["site_id"] == site_id]
    assert len(matching) == 1
    assert matching.iloc[0]["consumption_kwh"] == 5.0


def test_fetch_row_counts_increases_after_insert(db_engine, site_id):
    reader = PostgresTrainingDataReader(Config.DATABASE_URL, engine=db_engine)
    total_before, filtered_before = reader.fetch_row_counts()

    _insert_two_rows(db_engine, site_id)

    total_after, filtered_after = reader.fetch_row_counts()

    assert total_after == total_before + 2
    assert filtered_after == filtered_before + 1
