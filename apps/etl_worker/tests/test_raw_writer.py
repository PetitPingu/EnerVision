from unittest.mock import Mock

from infrastructure.raw_writer import RawWriter


def test_write_uses_date_site_id_timestamp_object_key():
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    object_key = writer.write(
        site_id="SITE001",
        timestamp="2026-09-15T10:00:13.879434",
        raw_payload=b'{"site_id": "SITE001"}',
    )

    assert object_key == "2026-09-15/SITE001_20260915T100013879434.json"


def test_write_puts_object_in_raw_bucket_with_raw_bytes():
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")
    raw_payload = b'{"site_id": "SITE001", "data_quality": "good"}'

    object_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:00:13.879434", raw_payload=raw_payload
    )

    client.put_object.assert_called_once()
    args, kwargs = client.put_object.call_args
    assert args[0] == "raw"
    assert args[1] == object_key
    assert kwargs["length"] == len(raw_payload)
    assert kwargs["content_type"] == "application/json"
    assert kwargs["data"].read() == raw_payload


def test_write_handles_timestamp_without_timezone():
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    object_key = writer.write(
        site_id="SITE003", timestamp="2026-01-05T03:20:00", raw_payload=b"{}"
    )

    assert object_key == "2026-01-05/SITE003_20260105T032000000000.json"


def test_write_does_not_overwrite_across_successive_calls():
    """Deux lectures du même site le même jour doivent produire deux objets
    distincts (pas d'écrasement), grâce à l'horodatage dans la clé."""
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    first_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:00:00.000000", raw_payload=b"{}"
    )
    second_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:01:00.000000", raw_payload=b"{}"
    )

    assert first_key != second_key
    assert client.put_object.call_count == 2
