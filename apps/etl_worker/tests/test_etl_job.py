from unittest.mock import Mock

from application.etl_job import EtlJob
from mockapi_client import EnergyReading, MockApiTimeoutError


def _reading(**overrides) -> EnergyReading:
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
    reading = EnergyReading(**data)
    reading.raw_payload = b'{"fake": "payload"}'
    return reading


def _critical_reading(**overrides) -> EnergyReading:
    return _reading(
        consumption_kw=None,
        consumption_kwh=None,
        voltage_v=None,
        current_a=None,
        power_factor=None,
        temperature_celsius=None,
        humidity_percent=None,
        null_reasons=["network_outage"],
        data_quality="critical",
        **overrides,
    )


def _job(**overrides):
    defaults = dict(api_client=Mock(), raw_writer=Mock())
    defaults.update(overrides)
    job = EtlJob(**defaults)
    job.raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"
    return job


def test_run_calls_get_readings_with_limit_7():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading()]
    job = _job(api_client=api_client)

    job.run()

    _, kwargs = api_client.get_readings.call_args
    assert kwargs["limit"] == 7


def test_process_writes_raw_payload_unmodified():
    reading = _reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()

    raw_writer.write.assert_called_once_with(
        site_id="SITE001", timestamp=reading.timestamp, raw_payload=reading.raw_payload
    )


def test_critical_reading_is_written_like_any_other():
    reading = _critical_reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()

    raw_writer.write.assert_called_once()


def test_raw_write_failure_does_not_crash():
    reading = _reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.side_effect = RuntimeError("minio down")

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()  # ne doit pas lever


def test_api_error_does_not_crash_and_writes_nothing():
    api_client = Mock()
    api_client.get_readings.side_effect = MockApiTimeoutError("timeout")
    raw_writer = Mock()

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()  # ne doit pas lever

    raw_writer.write.assert_not_called()


def test_run_processes_all_readings_returned():
    readings = [_reading(site_id=f"SITE00{i}") for i in range(1, 8)]
    api_client = Mock()
    api_client.get_readings.return_value = readings
    raw_writer = Mock()
    raw_writer.write.return_value = "x.json"

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()

    assert raw_writer.write.call_count == 7
