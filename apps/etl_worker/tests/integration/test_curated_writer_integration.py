"""Tests d'intégration de CuratedWriter contre un vrai Postgres (upsert réel).

Complète tests/test_curated_writer.py (engine mocké, logique de conversion
uniquement) : ici on vérifie que l'INSERT ... ON CONFLICT DO UPDATE réel se
comporte comme attendu contre TimescaleDB.
"""

import uuid
from datetime import datetime, timezone

import pytest
from db_schema.models import ReadingCurated
from sqlalchemy.orm import sessionmaker

from infrastructure.curated_writer import CuratedWriter

pytestmark = pytest.mark.integration


def _row(site_id: str, **overrides) -> dict:
    data = {
        "site_id": site_id,
        "timestamp": "2026-09-22T10:00:00+00:00",
        "site_type": "office",
        "consumption_kw": 12.5,
        "consumption_kwh": 1.5,
        "voltage_v": 230.0,
        "current_a": 5.4,
        "power_factor": 0.95,
        "temperature_celsius": 21.0,
        "humidity_percent": 40.0,
        "null_reasons": [],
        "data_quality": "good",
        "imputation_methods": None,
        **overrides,
    }
    return data


@pytest.fixture
def site_id():
    return f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _cleanup(db_engine, site_id):
    yield
    with db_engine.begin() as conn:
        conn.execute(ReadingCurated.__table__.delete().where(ReadingCurated.site_id == site_id))


def _get(db_engine, site_id: str, timestamp: datetime) -> ReadingCurated | None:
    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        return session.get(ReadingCurated, (site_id, timestamp))


def test_upsert_many_inserts_new_row(db_engine, site_id):
    writer = CuratedWriter(engine=db_engine)

    written = writer.upsert_many([_row(site_id)])

    assert written == 1
    row = _get(db_engine, site_id, datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc))
    assert row is not None
    assert row.consumption_kwh == 1.5
    assert row.data_quality == "good"


def test_upsert_many_on_conflict_updates_existing_row(db_engine, site_id):
    writer = CuratedWriter(engine=db_engine)
    writer.upsert_many([_row(site_id, consumption_kwh=1.5)])

    written = writer.upsert_many([_row(site_id, consumption_kwh=9.9, data_quality="critical")])

    assert written == 1
    row = _get(db_engine, site_id, datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc))
    assert row.consumption_kwh == 9.9
    assert row.data_quality == "critical"

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        count = session.query(ReadingCurated).filter(ReadingCurated.site_id == site_id).count()
    # Un seul enregistrement malgré les deux upserts : même clé (site_id, timestamp).
    assert count == 1


def test_upsert_many_different_timestamps_creates_separate_rows(db_engine, site_id):
    writer = CuratedWriter(engine=db_engine)

    writer.upsert_many(
        [
            _row(site_id, timestamp="2026-09-22T10:00:00+00:00"),
            _row(site_id, timestamp="2026-09-22T10:01:00+00:00"),
        ]
    )

    Session = sessionmaker(bind=db_engine)
    with Session() as session:
        count = session.query(ReadingCurated).filter(ReadingCurated.site_id == site_id).count()
    assert count == 2
