from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from application.historical_backfill import HistoricalBackfill
from mockapi_client import EnergyReading, MockApiTimeoutError


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


def test_run_calls_get_readings_with_date_range():
    api_client = Mock()
    api_client.get_readings.side_effect = [[_reading(timestamp="2026-01-01T12:00:00Z")], []]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    use_case = HistoricalBackfill(api_client=api_client, limit=500)

    readings = use_case.run(start, end)

    assert len(readings) == 1
    assert api_client.get_readings.call_args_list[0].kwargs == {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "limit": 500,
    }


def test_run_rejects_invalid_date_range():
    use_case = HistoricalBackfill(api_client=Mock())
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="strictement avant"):
        use_case.run(start, end)


def test_run_paginates_until_cursor_reaches_end():
    api_client = Mock()
    page1 = [_reading(timestamp="2026-01-01T10:00:00Z")]
    page2 = [_reading(timestamp="2026-01-01T11:00:00Z")]
    api_client.get_readings.side_effect = [page1, page2, []]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    use_case = HistoricalBackfill(api_client=api_client)

    readings = use_case.run(start, end)

    assert readings == page1 + page2
    assert api_client.get_readings.call_count == 3
    second_call = api_client.get_readings.call_args_list[1].kwargs
    assert second_call["start"] == "2026-01-01T10:00:00.000001+00:00"


def test_run_propagates_api_errors():
    api_client = Mock()
    api_client.get_readings.side_effect = MockApiTimeoutError("timeout")
    use_case = HistoricalBackfill(api_client=api_client)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(MockApiTimeoutError):
        use_case.run(start, end)
