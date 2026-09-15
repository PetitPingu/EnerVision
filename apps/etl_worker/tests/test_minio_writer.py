from unittest.mock import Mock

from infrastructure.minio_writer import BronzeWriter


def test_write_uses_year_month_day_hour_object_key():
    client = Mock()
    writer = BronzeWriter(client=client, bucket="bronze")

    object_key = writer.write(
        site_id="SITE001",
        timestamp="2026-09-15T10:00:13.879434",
        raw_payload=b'{"site_id": "SITE001"}',
    )

    assert object_key.startswith("2026/09/15/10/SITE001_20260915T100013879434")
    assert object_key.endswith(".json")


def test_write_puts_object_in_bronze_bucket_with_raw_bytes():
    client = Mock()
    writer = BronzeWriter(client=client, bucket="bronze")
    raw_payload = b'{"site_id": "SITE001", "data_quality": "good"}'

    object_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:00:13.879434", raw_payload=raw_payload
    )

    client.put_object.assert_called_once()
    args, kwargs = client.put_object.call_args
    assert args[0] == "bronze"
    assert args[1] == object_key
    assert kwargs["length"] == len(raw_payload)
    assert kwargs["content_type"] == "application/json"
    assert kwargs["data"].read() == raw_payload


def test_write_handles_timestamp_without_timezone():
    client = Mock()
    writer = BronzeWriter(client=client, bucket="bronze")

    object_key = writer.write(
        site_id="SITE003", timestamp="2026-01-05T03:20:00", raw_payload=b"{}"
    )

    assert object_key.startswith("2026/01/05/03/SITE003_")
