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
    defaults = dict(
        api_client=Mock(),
        raw_writer=Mock(),
        readings_writer=Mock(),
        alert_publisher=Mock(),
    )
    defaults.update(overrides)
    job = EtlJob(**defaults)
    job.raw_writer.write.return_value = "2026-09-15/SITE001_20260915T100013879434.json"
    job.readings_writer.insert.return_value = True
    return job


def test_run_calls_get_readings_with_limit_7():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading()]
    job = _job(api_client=api_client)

    job.run()

    _, kwargs = api_client.get_readings.call_args
    assert kwargs["limit"] == 7


def test_process_writes_raw_and_inserts_in_db():
    reading = _reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "2026-09-15/SITE001_x.json"
    readings_writer = Mock()
    readings_writer.insert.return_value = True
    alert_publisher = Mock()

    job = _job(
        api_client=api_client,
        raw_writer=raw_writer,
        readings_writer=readings_writer,
        alert_publisher=alert_publisher,
    )
    job.run()

    raw_writer.write.assert_called_once_with(
        site_id="SITE001", timestamp=reading.timestamp, raw_payload=reading.raw_payload
    )
    readings_writer.insert.assert_called_once_with(reading)
    alert_publisher.publish.assert_not_called()  # data_quality "good" : pas d'alerte


def test_process_publishes_alert_for_critical_reading():
    reading = _critical_reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    alert_publisher = Mock()

    job = _job(api_client=api_client, alert_publisher=alert_publisher)
    job.run()

    alert_publisher.publish.assert_called_once_with(reading)


def test_critical_reading_is_still_written_and_inserted_not_skipped():
    reading = _critical_reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "2026-09-15/SITE001_x.json"
    readings_writer = Mock()
    readings_writer.insert.return_value = True

    job = _job(api_client=api_client, raw_writer=raw_writer, readings_writer=readings_writer)
    job.run()

    raw_writer.write.assert_called_once()
    readings_writer.insert.assert_called_once_with(reading)


def test_db_failure_does_not_prevent_raw_write_or_alert():
    reading = _critical_reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "2026-09-15/SITE001_x.json"
    readings_writer = Mock()
    readings_writer.insert.side_effect = RuntimeError("db down")
    alert_publisher = Mock()

    job = _job(
        api_client=api_client,
        raw_writer=raw_writer,
        readings_writer=readings_writer,
        alert_publisher=alert_publisher,
    )
    job.run()  # ne doit pas lever

    raw_writer.write.assert_called_once()
    alert_publisher.publish.assert_called_once_with(reading)


def test_alert_failure_does_not_prevent_db_insert():
    reading = _critical_reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    readings_writer = Mock()
    readings_writer.insert.return_value = True
    alert_publisher = Mock()
    alert_publisher.publish.side_effect = RuntimeError("redis down")

    job = _job(api_client=api_client, readings_writer=readings_writer, alert_publisher=alert_publisher)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_called_once_with(reading)


def test_raw_write_failure_skips_reading_without_crashing():
    reading = _reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.side_effect = RuntimeError("minio down")
    readings_writer = Mock()

    job = _job(api_client=api_client, raw_writer=raw_writer, readings_writer=readings_writer)
    job.run()  # ne doit pas lever

    readings_writer.insert.assert_not_called()


def test_api_error_does_not_crash_and_writes_nothing():
    api_client = Mock()
    api_client.get_readings.side_effect = MockApiTimeoutError("timeout")
    raw_writer = Mock()

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()  # ne doit pas lever

    raw_writer.write.assert_not_called()
