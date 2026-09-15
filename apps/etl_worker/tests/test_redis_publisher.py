import json
from unittest.mock import Mock

from infrastructure.redis_publisher import STREAM_NAME, ReadingIngestedPublisher
from mockapi_client import EnergyReading


def _reading() -> EnergyReading:
    return EnergyReading(
        timestamp="2026-09-15T10:00:13.879434",
        site_id="SITE001",
        site_type="office",
        consumption_kw=154.4,
        consumption_kwh=154.4,
        voltage_v=404.4,
        current_a=232.04,
        power_factor=0.946,
        temperature_celsius=8.5,
        humidity_percent=38.0,
        null_reasons=[],
        data_quality="good",
    )


def test_publish_xadds_to_reading_ingested_stream():
    client = Mock()
    publisher = ReadingIngestedPublisher(client=client)
    reading = _reading()

    publisher.publish(reading)

    client.xadd.assert_called_once()
    stream_name, fields = client.xadd.call_args[0]
    assert stream_name == STREAM_NAME
    assert fields["site_id"] == "SITE001"
    assert fields["data_quality"] == "good"
    assert json.loads(fields["payload"])["site_id"] == "SITE001"
