"""Tests de infrastructure/alert_publisher.py : XADD sur alert.detected,
avec un client Redis factice (pas de vrai Redis)."""

import json
from unittest.mock import Mock

from infrastructure.alert_publisher import STREAM_MAXLEN, STREAM_NAME, AlertPublisher


def test_publish_sends_xadd_on_the_right_stream_with_trim():
    client = Mock()
    publisher = AlertPublisher(client=client)

    publisher.publish(
        site_id="SITE001",
        timestamp="2026-09-15T10:00:00",
        data_quality="critical",
        null_reasons=["network_outage"],
    )

    args, kwargs = client.xadd.call_args
    assert args[0] == STREAM_NAME
    assert kwargs["maxlen"] == STREAM_MAXLEN
    assert kwargs["approximate"] is True


def test_publish_sends_flat_string_fields_and_json_encoded_null_reasons():
    client = Mock()
    publisher = AlertPublisher(client=client)

    publisher.publish(
        site_id="SITE001",
        timestamp="2026-09-15T10:00:00",
        data_quality="critical",
        null_reasons=["network_outage", "sensor_fault"],
    )

    args, _ = client.xadd.call_args
    fields = args[1]
    assert fields["site_id"] == "SITE001"
    assert fields["timestamp"] == "2026-09-15T10:00:00"
    assert fields["data_quality"] == "critical"
    assert json.loads(fields["null_reasons"]) == ["network_outage", "sensor_fault"]


def test_publish_with_empty_null_reasons_does_not_raise():
    client = Mock()
    publisher = AlertPublisher(client=client)

    publisher.publish(
        site_id="SITE001", timestamp="2026-09-15T10:00:00", data_quality="good", null_reasons=[]
    )

    args, _ = client.xadd.call_args
    assert json.loads(args[1]["null_reasons"]) == []
