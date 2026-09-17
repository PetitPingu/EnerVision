from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from application.historical_backfill import HistoricalBackfill
from domain.imputation import ConsumptionKwhImputer
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


def _backfill(**overrides):
    defaults = dict(
        api_client=Mock(),
        raw_writer=Mock(),
        curated_writer=Mock(),
    )
    defaults.update(overrides)
    backfill = HistoricalBackfill(**defaults)
    backfill.raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"
    return backfill


def test_run_calls_get_readings_with_date_range():
    api_client = Mock()
    api_client.get_readings.side_effect = [[_reading(timestamp="2026-01-01T12:00:00Z")], []]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    backfill = _backfill(api_client=api_client, limit=500)

    stats = backfill.run(start, end)

    assert stats == {"fetched": 1, "curated": 1, "skipped": 0}
    assert api_client.get_readings.call_args_list[0].kwargs == {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "limit": 500,
    }


def test_run_rejects_invalid_date_range():
    backfill = _backfill()
    start = datetime(2026, 1, 2, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="strictement avant"):
        backfill.run(start, end)


def test_run_paginates_and_upserts_each_page():
    api_client = Mock()
    page1 = [_reading(timestamp="2026-01-01T10:00:00Z")]
    page2 = [_reading(timestamp="2026-01-01T11:00:00Z")]
    api_client.get_readings.side_effect = [page1, page2, []]
    curated_writer = Mock()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    backfill = _backfill(api_client=api_client, curated_writer=curated_writer)

    stats = backfill.run(start, end)

    assert stats == {"fetched": 2, "curated": 2, "skipped": 0}
    assert curated_writer.upsert_many.call_count == 2
    second_call = api_client.get_readings.call_args_list[1].kwargs
    assert second_call["start"] == "2026-01-01T10:00:00.000001+00:00"


def test_run_writes_raw_payload_for_each_reading():
    reading = _reading(timestamp="2026-01-01T12:00:00Z")
    api_client = Mock()
    api_client.get_readings.side_effect = [[reading], []]
    raw_writer = Mock()
    raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"
    backfill = _backfill(api_client=api_client, raw_writer=raw_writer)

    backfill.run(datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc))

    raw_writer.write.assert_called_once_with(
        site_id="SITE001", timestamp=reading.timestamp, raw_payload=reading.raw_payload
    )


def test_raw_write_failure_skips_reading_but_continues():
    reading = _reading(timestamp="2026-01-01T12:00:00Z")
    api_client = Mock()
    api_client.get_readings.side_effect = [[reading], []]
    raw_writer = Mock()
    raw_writer.write.side_effect = RuntimeError("minio down")
    curated_writer = Mock()
    backfill = _backfill(api_client=api_client, raw_writer=raw_writer, curated_writer=curated_writer)

    stats = backfill.run(datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc))

    assert stats == {"fetched": 1, "curated": 0, "skipped": 1}
    curated_writer.upsert_many.assert_not_called()


def test_forward_fill_works_across_pages():
    api_client = Mock()
    api_client.get_readings.side_effect = [
        [_reading(timestamp="2026-01-01T10:00:00Z", consumption_kwh=42.0)],
        [_reading(timestamp="2026-01-01T11:00:00Z", consumption_kwh=None, data_quality="partial")],
        [],
    ]
    curated_writer = Mock()
    imputer = ConsumptionKwhImputer()
    backfill = _backfill(api_client=api_client, curated_writer=curated_writer, imputer=imputer)

    backfill.run(datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc))

    second_upsert = curated_writer.upsert_many.call_args_list[1].args[0][0]
    assert second_upsert["consumption_kwh"] == 42.0
    assert second_upsert["imputation_methods"] == "forward_fill"


def test_run_propagates_api_errors():
    api_client = Mock()
    api_client.get_readings.side_effect = MockApiTimeoutError("timeout")
    backfill = _backfill(api_client=api_client)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(MockApiTimeoutError):
        backfill.run(start, end)


def test_curated_write_failure_stops_backfill_with_partial_stats():
    api_client = Mock()
    api_client.get_readings.side_effect = [
        [_reading(timestamp="2026-01-01T10:00:00Z")],
        [_reading(timestamp="2026-01-01T11:00:00Z")],
        [],
    ]
    curated_writer = Mock()
    curated_writer.upsert_many.side_effect = [1, RuntimeError("postgres down")]
    backfill = _backfill(api_client=api_client, curated_writer=curated_writer)

    stats = backfill.run(datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc))

    assert stats == {"fetched": 2, "curated": 1, "skipped": 0}
    assert curated_writer.upsert_many.call_count == 2
