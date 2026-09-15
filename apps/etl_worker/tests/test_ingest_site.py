from unittest.mock import Mock

from application.ingest_site import SiteIngestor
from mockapi_client import EnergyReading, MockApiTimeoutError
from mockapi_client import Site as MockSite


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


def _ingestor(**overrides):
    defaults = dict(
        api_client=Mock(),
        bronze_writer=Mock(),
        readings_writer=Mock(),
        event_publisher=Mock(),
    )
    defaults.update(overrides)
    return SiteIngestor(**defaults)


def test_ingest_site_writes_bronze_postgres_and_publishes_event():
    reading = _reading()
    api_client = Mock()
    api_client.get_current.return_value = reading
    bronze_writer = Mock()
    bronze_writer.write.return_value = "2026/09/15/10/SITE001_20260915T100013879434.json"
    readings_writer = Mock()
    readings_writer.insert.return_value = True
    event_publisher = Mock()

    ingestor = _ingestor(
        api_client=api_client,
        bronze_writer=bronze_writer,
        readings_writer=readings_writer,
        event_publisher=event_publisher,
    )

    ingestor.ingest_site("SITE001")

    api_client.get_current.assert_called_once_with("SITE001")
    readings_writer.insert.assert_called_once_with(reading)
    bronze_writer.write.assert_called_once_with(
        site_id="SITE001", timestamp=reading.timestamp, raw_payload=reading.raw_payload
    )
    event_publisher.publish.assert_called_once_with(reading)


def test_ingest_site_critical_reading_is_still_ingested_not_skipped():
    critical_reading = _reading(
        consumption_kw=None,
        consumption_kwh=None,
        voltage_v=None,
        current_a=None,
        power_factor=None,
        temperature_celsius=None,
        humidity_percent=None,
        null_reasons=["network_outage"],
        data_quality="critical",
    )
    api_client = Mock()
    api_client.get_current.return_value = critical_reading
    readings_writer = Mock()
    readings_writer.insert.return_value = True
    bronze_writer = Mock()
    bronze_writer.write.return_value = "2026/09/15/10/SITE002_20260915T100013879434.json"
    event_publisher = Mock()

    ingestor = _ingestor(
        api_client=api_client,
        readings_writer=readings_writer,
        bronze_writer=bronze_writer,
        event_publisher=event_publisher,
    )

    ingestor.ingest_site("SITE002")

    readings_writer.insert.assert_called_once_with(critical_reading)
    bronze_writer.write.assert_called_once()
    event_publisher.publish.assert_called_once_with(critical_reading)


def test_ingest_site_skips_bronze_and_event_on_duplicate():
    reading = _reading()
    api_client = Mock()
    api_client.get_current.return_value = reading
    readings_writer = Mock()
    readings_writer.insert.return_value = False  # ON CONFLICT DO NOTHING a matché
    bronze_writer = Mock()
    event_publisher = Mock()

    ingestor = _ingestor(
        api_client=api_client,
        readings_writer=readings_writer,
        bronze_writer=bronze_writer,
        event_publisher=event_publisher,
    )

    ingestor.ingest_site("SITE001")

    bronze_writer.write.assert_not_called()
    event_publisher.publish.assert_not_called()


def test_ingest_site_api_error_does_not_crash_and_writes_nothing():
    api_client = Mock()
    api_client.get_current.side_effect = MockApiTimeoutError("timeout")
    bronze_writer = Mock()
    readings_writer = Mock()
    event_publisher = Mock()

    ingestor = _ingestor(
        api_client=api_client,
        bronze_writer=bronze_writer,
        readings_writer=readings_writer,
        event_publisher=event_publisher,
    )

    ingestor.ingest_site("SITE001")  # ne doit pas lever

    bronze_writer.write.assert_not_called()
    readings_writer.insert.assert_not_called()
    event_publisher.publish.assert_not_called()


def test_ingest_site_infra_failure_does_not_crash():
    reading = _reading()
    api_client = Mock()
    api_client.get_current.return_value = reading
    readings_writer = Mock()
    readings_writer.insert.side_effect = RuntimeError("db down")

    ingestor = _ingestor(api_client=api_client, readings_writer=readings_writer)

    ingestor.ingest_site("SITE001")  # ne doit pas lever


def _mock_site(site_id: str) -> MockSite:
    return MockSite(
        site_id=site_id,
        site_type="office",
        site_name="Bureau",
        location="Paris",
        capacity_kw=200.0,
        status="active",
    )


def test_ingest_all_sites_continues_when_one_site_fails():
    api_client = Mock()
    api_client.get_sites.return_value = [_mock_site("SITE001"), _mock_site("SITE002")]
    api_client.get_current.side_effect = [
        MockApiTimeoutError("timeout"),
        _reading(site_id="SITE002"),
    ]
    readings_writer = Mock()
    readings_writer.insert.return_value = True
    bronze_writer = Mock()
    bronze_writer.write.return_value = "2026/09/15/10/SITE002_20260915T100013879434.json"

    ingestor = _ingestor(
        api_client=api_client, readings_writer=readings_writer, bronze_writer=bronze_writer
    )

    ingestor.ingest_all_sites()

    assert api_client.get_current.call_count == 2
    readings_writer.insert.assert_called_once()


def test_ingest_all_sites_handles_get_sites_failure_without_crash():
    api_client = Mock()
    api_client.get_sites.side_effect = MockApiTimeoutError("timeout")

    ingestor = _ingestor(api_client=api_client)

    ingestor.ingest_all_sites()  # ne doit pas lever

    api_client.get_current.assert_not_called()
