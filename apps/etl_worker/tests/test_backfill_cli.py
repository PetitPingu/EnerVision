from datetime import datetime, timezone

from backfill import main, parse_datetime


def test_parse_datetime_accepts_date_only():
    assert parse_datetime("2024-01-01") == datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_parse_datetime_accepts_iso_with_timezone():
    assert parse_datetime("2026-09-17T10:00:00Z") == datetime(
        2026, 9, 17, 10, 0, tzinfo=timezone.utc
    )


def test_main_rejects_invalid_date_range():
    assert main(["--start", "2026-01-02", "--end", "2026-01-01"]) == 1


def test_main_runs_backfill_with_parsed_dates():
    from unittest.mock import patch

    with patch("backfill.HistoricalBackfill") as mock_cls:
        mock_cls.return_value.run.return_value = {"fetched": 3, "curated": 2, "skipped": 1}
        exit_code = main(["--start", "2024-01-01", "--end", "2024-01-02"])

    assert exit_code == 0
    mock_cls.return_value.run.assert_called_once()
    start, end = mock_cls.return_value.run.call_args.args
    assert start == datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert end == datetime(2024, 1, 2, tzinfo=timezone.utc)
