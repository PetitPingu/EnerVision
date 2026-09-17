from datetime import date
from unittest.mock import Mock

import pytest

from application.historical_backfill import DEFAULT_LIMIT, HistoricalBackfill
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


def test_run_makes_one_api_call_per_day_with_limit_1000():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading()]
    backfill = _backfill(api_client=api_client)

    stats = backfill.run(date(2026, 9, 16), date(2026, 9, 17))

    assert stats == {"fetched": 2, "curated": 2, "skipped": 0, "days_done": 2}
    assert api_client.get_readings.call_count == 2
    assert api_client.get_readings.call_args_list[0].kwargs == {
        "start": "2026-09-16T00:00:00+00:00",
        "end": "2026-09-17T00:00:00+00:00",
        "limit": DEFAULT_LIMIT,
    }
    assert api_client.get_readings.call_args_list[1].kwargs == {
        "start": "2026-09-17T00:00:00+00:00",
        "end": "2026-09-18T00:00:00+00:00",
        "limit": DEFAULT_LIMIT,
    }


def test_run_single_day_makes_exactly_one_call():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading()]
    backfill = _backfill(api_client=api_client)

    stats = backfill.run(date(2026, 9, 16), date(2026, 9, 16))

    assert stats["days_done"] == 1
    assert api_client.get_readings.call_count == 1


def test_run_rejects_invalid_date_range():
    backfill = _backfill()

    with pytest.raises(ValueError, match="avant ou égal"):
        backfill.run(date(2026, 9, 17), date(2026, 9, 16))


def test_run_writes_raw_payload_for_each_reading():
    reading = _reading(timestamp="2026-09-16T12:00:00Z")
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"
    backfill = _backfill(api_client=api_client, raw_writer=raw_writer)

    backfill.run(date(2026, 9, 16), date(2026, 9, 16))

    raw_writer.write.assert_called_once_with(
        site_id="SITE001", timestamp=reading.timestamp, raw_payload=reading.raw_payload
    )


def test_raw_write_failure_skips_reading_but_continues_next_day():
    api_client = Mock()
    api_client.get_readings.side_effect = [
        [_reading(timestamp="2026-09-16T12:00:00Z")],
        [_reading(timestamp="2026-09-17T12:00:00Z")],
    ]
    raw_writer = Mock()
    raw_writer.write.side_effect = RuntimeError("minio down")
    curated_writer = Mock()
    backfill = _backfill(api_client=api_client, raw_writer=raw_writer, curated_writer=curated_writer)

    stats = backfill.run(date(2026, 9, 16), date(2026, 9, 17))

    assert stats == {"fetched": 2, "curated": 0, "skipped": 2, "days_done": 2}
    assert api_client.get_readings.call_count == 2
    curated_writer.upsert_many.assert_not_called()


def test_forward_fill_works_across_days():
    api_client = Mock()
    api_client.get_readings.side_effect = [
        [_reading(timestamp="2026-09-16T10:00:00Z", consumption_kwh=42.0)],
        [_reading(timestamp="2026-09-17T10:00:00Z", consumption_kwh=None, data_quality="partial")],
    ]
    curated_writer = Mock()
    imputer = ConsumptionKwhImputer()
    backfill = _backfill(api_client=api_client, curated_writer=curated_writer, imputer=imputer)

    backfill.run(date(2026, 9, 16), date(2026, 9, 17))

    second_upsert = curated_writer.upsert_many.call_args_list[1].args[0][0]
    assert second_upsert["consumption_kwh"] == 42.0
    assert second_upsert["imputation_methods"] == "forward_fill"


def test_run_propagates_api_errors():
    api_client = Mock()
    api_client.get_readings.side_effect = MockApiTimeoutError("timeout")
    backfill = _backfill(api_client=api_client)

    with pytest.raises(MockApiTimeoutError):
        backfill.run(date(2026, 9, 16), date(2026, 9, 17))


def test_curated_write_failure_stops_backfill_with_partial_stats():
    api_client = Mock()
    api_client.get_readings.side_effect = [
        [_reading(timestamp="2026-09-16T10:00:00Z")],
        [_reading(timestamp="2026-09-17T10:00:00Z")],
    ]
    curated_writer = Mock()
    curated_writer.upsert_many.side_effect = [1, RuntimeError("postgres down")]
    backfill = _backfill(api_client=api_client, curated_writer=curated_writer)

    stats = backfill.run(date(2026, 9, 16), date(2026, 9, 17))

    assert stats == {"fetched": 2, "curated": 1, "skipped": 0, "days_done": 1}
    assert api_client.get_readings.call_count == 2
    assert curated_writer.upsert_many.call_count == 2
