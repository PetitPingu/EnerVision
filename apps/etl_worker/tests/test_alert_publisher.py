from unittest.mock import Mock

from infrastructure.alert_publisher import STREAM_NAME, AlertPublisher
from mockapi_client import EnergyReading


def _reading(**overrides) -> EnergyReading:
    data = {
        "timestamp": "2026-09-15T10:00:13.879434",
        "site_id": "SITE001",
        "site_type": "office",
        "consumption_kw": None,
        "consumption_kwh": None,
        "voltage_v": None,
        "current_a": None,
        "power_factor": None,
        "temperature_celsius": None,
        "humidity_percent": None,
        "null_reasons": ["network_outage"],
        "data_quality": "critical",
        **overrides,
    }
    return EnergyReading(**data)


def test_publish_xadds_to_alert_detected_stream():
    client = Mock()
    publisher = AlertPublisher(client=client)
    reading = _reading()

    publisher.publish(reading)

    client.xadd.assert_called_once()
    stream_name, fields = client.xadd.call_args[0]
    assert stream_name == STREAM_NAME
    assert fields["site_id"] == "SITE001"
    assert fields["timestamp"] == reading.timestamp
    assert fields["data_quality"] == "critical"
