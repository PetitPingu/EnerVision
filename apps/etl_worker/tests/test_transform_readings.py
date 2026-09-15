import json
from unittest.mock import Mock

from application.transform_readings import HourlyTransformationJob


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


def _job(**overrides):
    defaults = dict(raw_reader=Mock(), readings_writer=Mock())
    defaults.update(overrides)
    return HourlyTransformationJob(**defaults)


def test_run_inserts_valid_readings_from_raw_bucket():
    raw_reader = Mock()
    raw_reader.read_date.return_value = [_reading_json(), _reading_json(site_id="SITE002")]
    readings_writer = Mock()
    readings_writer.insert.return_value = True

    job = _job(raw_reader=raw_reader, readings_writer=readings_writer)
    job.run()

    assert readings_writer.insert.call_count == 2


def test_run_counts_duplicates_without_error():
    raw_reader = Mock()
    raw_reader.read_date.return_value = [_reading_json()]
    readings_writer = Mock()
    readings_writer.insert.return_value = False  # déjà transformé lors d'un run précédent

    job = _job(raw_reader=raw_reader, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_called_once()


def test_run_skips_invalid_json_without_crashing():
    raw_reader = Mock()
    raw_reader.read_date.return_value = [b"not valid json", _reading_json()]
    readings_writer = Mock()
    readings_writer.insert.return_value = True

    job = _job(raw_reader=raw_reader, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_called_once()  # seul le JSON valide est passé au writer


def test_run_skips_payload_failing_pydantic_validation():
    raw_reader = Mock()
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
    raw_reader.read_date.return_value = [invalid_payload]
    readings_writer = Mock()

    job = _job(raw_reader=raw_reader, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_not_called()


def test_run_with_no_files_does_not_crash():
    raw_reader = Mock()
    raw_reader.read_date.return_value = []
    readings_writer = Mock()

    job = _job(raw_reader=raw_reader, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_not_called()
