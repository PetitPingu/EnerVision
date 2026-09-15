import json
from unittest.mock import Mock

from application.transform_readings import HourlyTransformationJob
from mockapi_client import MockApiTimeoutError
from mockapi_client import Site as MockSite


def _reading_json(**overrides) -> bytes:
    data = {
        "timestamp": "2026-09-15T10:00:13.879434",
        "site_id": "SITE001",
        "site_type": "office",
        "consumption_kw": 154.4,
        "consumption_kwh": 154.4,
        "voltage_v": 404.4,
        "current_a": 232.04,
        "power_factor": 0.946,
        "temperature_celsius": 8.5,
        "humidity_percent": 38.0,
        "null_reasons": [],
        "data_quality": "good",
        **overrides,
    }
    return json.dumps(data).encode("utf-8")


def _mock_site(site_id: str) -> MockSite:
    return MockSite(
        site_id=site_id,
        site_type="office",
        site_name="Bureau",
        location="Paris",
        capacity_kw=200.0,
        status="active",
    )


def _job(**overrides):
    defaults = dict(
        api_client=Mock(),
        bronze_reader=Mock(),
        sites_writer=Mock(),
        readings_writer=Mock(),
    )
    defaults.update(overrides)
    return HourlyTransformationJob(**defaults)


def test_run_syncs_sites_before_transforming():
    api_client = Mock()
    api_client.get_sites.return_value = [_mock_site("SITE001"), _mock_site("SITE002")]
    bronze_reader = Mock()
    bronze_reader.read_hour.return_value = []
    sites_writer = Mock()

    job = _job(api_client=api_client, bronze_reader=bronze_reader, sites_writer=sites_writer)
    job.run()

    sites_writer.upsert_all.assert_called_once_with(
        [_mock_site("SITE001"), _mock_site("SITE002")]
    )


def test_run_inserts_valid_readings_from_bronze():
    bronze_reader = Mock()
    bronze_reader.read_hour.return_value = [_reading_json(), _reading_json(site_id="SITE002")]
    readings_writer = Mock()
    readings_writer.insert.return_value = True

    job = _job(bronze_reader=bronze_reader, readings_writer=readings_writer)
    job.run()

    assert readings_writer.insert.call_count == 2


def test_run_counts_duplicates_without_error():
    bronze_reader = Mock()
    bronze_reader.read_hour.return_value = [_reading_json()]
    readings_writer = Mock()
    readings_writer.insert.return_value = False  # déjà transformé lors d'un run précédent

    job = _job(bronze_reader=bronze_reader, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_called_once()


def test_run_skips_invalid_json_without_crashing():
    bronze_reader = Mock()
    bronze_reader.read_hour.return_value = [b"not valid json", _reading_json()]
    readings_writer = Mock()
    readings_writer.insert.return_value = True

    job = _job(bronze_reader=bronze_reader, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_called_once()  # seul le JSON valide est passé au writer


def test_run_skips_payload_failing_pydantic_validation():
    bronze_reader = Mock()
    invalid_payload = json.dumps(
        {
            "timestamp": "2026-09-15T10:00:13.879434",
            "site_id": "SITE001",
            "site_type": "office",
            # champs de mesure manquants -> ValidationError (pas de defaut silencieux)
            "null_reasons": [],
            "data_quality": "good",
        }
    ).encode("utf-8")
    bronze_reader.read_hour.return_value = [invalid_payload]
    readings_writer = Mock()

    job = _job(bronze_reader=bronze_reader, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_not_called()


def test_sites_sync_error_does_not_block_transformation():
    api_client = Mock()
    api_client.get_sites.side_effect = MockApiTimeoutError("timeout")
    bronze_reader = Mock()
    bronze_reader.read_hour.return_value = [_reading_json()]
    readings_writer = Mock()
    readings_writer.insert.return_value = True
    sites_writer = Mock()

    job = _job(
        api_client=api_client,
        bronze_reader=bronze_reader,
        readings_writer=readings_writer,
        sites_writer=sites_writer,
    )
    job.run()  # ne doit pas lever

    sites_writer.upsert_all.assert_not_called()
    readings_writer.insert.assert_called_once()
