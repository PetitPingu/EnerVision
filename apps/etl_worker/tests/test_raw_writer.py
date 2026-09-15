from unittest.mock import Mock

from infrastructure.raw_writer import RawWriter


def test_write_uses_year_month_day_hour_object_key_in_local_time():
    """2026-09-15T10:00 UTC -> 12:00 heure locale (Europe/Paris, CEST en été)."""
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    object_key = writer.write(
        site_id="SITE001",
        timestamp="2026-09-15T10:00:13.879434",
        raw_payload=b'{"site_id": "SITE001"}',
    )

    assert object_key == "2026/09/15/12/001_00.json"


def test_write_filename_uses_site_number_and_minutes():
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    object_key = writer.write(
        site_id="SITE003",
        timestamp="2026-09-15T12:26:13.879434",
        raw_payload=b"{}",
    )

    assert object_key == "2026/09/15/14/003_26.json"


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
    """2026-01-05T03:20 UTC (traité comme UTC, sans tz) -> 04:20 heure locale (CET en hiver)."""
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    object_key = writer.write(
        site_id="SITE003", timestamp="2026-01-05T03:20:00", raw_payload=b"{}"
    )

    assert object_key == "2026/01/05/04/003_20.json"


def test_write_overwrites_within_the_same_minute():
    """Compromis assumé : deux lectures du même site dans la même minute
    partagent la même clé (contrairement à l'horodatage complet)."""
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    first_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:00:00.000000", raw_payload=b"{}"
    )
    second_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:00:45.000000", raw_payload=b"{}"
    )

    assert first_key == second_key


def test_write_does_not_collide_across_different_minutes():
    client = Mock()
    writer = RawWriter(client=client, bucket="raw")

    first_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:00:00.000000", raw_payload=b"{}"
    )
    second_key = writer.write(
        site_id="SITE001", timestamp="2026-09-15T10:01:00.000000", raw_payload=b"{}"
    )

    assert first_key != second_key
