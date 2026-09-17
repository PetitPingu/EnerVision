from datetime import date

from backfill import main, parse_date


def test_parse_date_accepts_yyyy_mm_dd():
    assert parse_date("2024-05-28") == date(2024, 5, 28)


def test_main_rejects_invalid_date_range():
    assert main(["--start", "2026-09-17", "--end", "2026-09-16"]) == 1


def test_main_runs_backfill_with_parsed_dates():
    from unittest.mock import patch

    with patch("backfill.HistoricalBackfill") as mock_cls:
        mock_cls.return_value.run.return_value = {
            "fetched": 3,
            "curated": 2,
            "skipped": 1,
            "days_done": 2,
        }
        exit_code = main(["--start", "2026-09-16", "--end", "2026-09-17"])

    assert exit_code == 0
    mock_cls.return_value.run.assert_called_once_with(date(2026, 9, 16), date(2026, 9, 17))
