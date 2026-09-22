"""Tests d'intégration de RawWriter/RawReader contre un vrai MinIO (roundtrip réel).

Complète tests/test_raw_writer.py (client mocké, calcul de la clé objet
uniquement) : ici on vérifie l'écriture/lecture réelle du bucket, que les
mocks ne peuvent pas couvrir (sérialisation, présence du bucket...).
"""

import json
import uuid

import pytest

from infrastructure.raw_reader import RawReader
from infrastructure.raw_writer import RawWriter

pytestmark = pytest.mark.integration


def _payload(site_id: str) -> bytes:
    return json.dumps(
        {
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
            "data_quality": "good",
            "null_reasons": [],
        }
    ).encode("utf-8")


@pytest.fixture
def site_id():
    return f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _cleanup(minio_client, site_id):
    yield
    for obj in minio_client.list_objects("raw", prefix=site_id, recursive=True):
        minio_client.remove_object("raw", obj.object_name)


def test_write_then_list_then_read_round_trips(minio_client, site_id):
    writer = RawWriter(client=minio_client, bucket="raw")
    reader = RawReader(client=minio_client, bucket="raw")
    payload = _payload(site_id)

    object_key = writer.write(
        site_id=site_id, timestamp="2026-09-22T10:00:00+00:00", raw_payload=payload
    )

    keys = reader.list_object_keys(prefix=site_id)
    assert keys == [object_key]

    reading = reader.read_object(object_key)
    assert reading.site_id == site_id
    assert reading.raw_payload == payload


def test_list_object_keys_returns_sorted_keys_for_prefix(minio_client, site_id):
    writer = RawWriter(client=minio_client, bucket="raw")
    reader = RawReader(client=minio_client, bucket="raw")
    writer.write(
        site_id=site_id, timestamp="2026-09-22T10:05:00+00:00", raw_payload=_payload(site_id)
    )
    writer.write(
        site_id=site_id, timestamp="2026-09-22T10:00:00+00:00", raw_payload=_payload(site_id)
    )

    keys = reader.list_object_keys(prefix=site_id)

    assert len(keys) == 2
    assert keys == sorted(keys)
