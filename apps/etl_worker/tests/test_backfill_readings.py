from datetime import datetime
from unittest.mock import Mock, patch

from application.backfill_readings import BackfillReadingsJob, build_parser, iter_hourly_windows
from mockapi_client.models import EnergyReading


def test_iter_hourly_windows_splits_two_hours():
    start = datetime(2024, 1, 1, 0, 0, 0)
    end = datetime(2024, 1, 1, 2, 0, 0)

    windows = list(iter_hourly_windows(start, end))

    assert windows == [
        (datetime(2024, 1, 1, 0, 0, 0), datetime(2024, 1, 1, 1, 0, 0)),
        (datetime(2024, 1, 1, 1, 0, 0), datetime(2024, 1, 1, 2, 0, 0)),
    ]


def test_backfill_fetches_hourly_without_site_and_writes_to_raw():
    api_client = Mock()
    raw_writer = Mock()
    raw_writer._client = Mock()
    raw_writer._client.bucket_exists.return_value = True
    raw_writer._bucket = "raw"

    reading = EnergyReading(
        timestamp="2024-01-01T00:00:00.123456",
        site_id="SITE001",
        site_type="factory",
        consumption_kw=10.0,
        consumption_kwh=0.5,
        voltage_v=230.0,
        current_a=5.0,
        power_factor=0.95,
        temperature_celsius=20.0,
        humidity_percent=50.0,
        null_reasons=[],
        data_quality="good",
    )
    reading.raw_payload = b'{"site_id": "SITE001"}'
    api_client.get_readings.return_value = [reading]

    job = BackfillReadingsJob(
        api_client=api_client,
        raw_writer=raw_writer,
        start_time="2024-01-01T00:00:00",
        end_time="2024-01-01T01:00:00",
        hourly_limit=420,
    )

    with patch("application.backfill_readings._ensure_bucket"):
        job.run()

    api_client.get_readings.assert_called_once_with(
        start="2024-01-01T00:00:00",
        end="2024-01-01T01:00:00",
        limit=420,
    )
    raw_writer.write.assert_called_once_with(
        site_id="SITE001",
        timestamp="2024-01-01T00:00:00.123456",
        raw_payload=b'{"site_id": "SITE001"}',
    )


def test_build_parser_parses_backfill_args():
    args = build_parser().parse_args(
        [
            "--start",
            "2024-01-01T00:00:00",
            "--end",
            "2026-01-01T00:00:00",
        ]
    )

    assert args.start == "2024-01-01T00:00:00"
    assert args.end == "2026-01-01T00:00:00"
    assert args.limit == 420
