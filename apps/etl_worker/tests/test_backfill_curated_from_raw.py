from datetime import datetime, timezone
from unittest.mock import Mock

from application.backfill_curated_from_raw import (
    BackfillCuratedFromRawJob,
    _in_range,
    build_parser,
    reading_to_curated_row,
)
from domain.imputation import ConsumptionKwhImputer
from mockapi_client import EnergyReading


def _reading(**overrides) -> EnergyReading:
    data = {
        "timestamp": "2024-01-01T00:00:00",
        "site_id": "SITE001",
        "site_type": "factory",
        "consumption_kw": 10.0,
        "consumption_kwh": 0.5,
        "voltage_v": 230.0,
        "current_a": 5.0,
        "power_factor": 0.95,
        "temperature_celsius": 20.0,
        "humidity_percent": 50.0,
        "null_reasons": [],
        "data_quality": "good",
        **overrides,
    }
    reading = EnergyReading(**data)
    reading.raw_payload = b"{}"
    return reading


def test_reading_to_curated_row_applies_forward_fill_in_order():
    imputer = ConsumptionKwhImputer()
    first = reading_to_curated_row(_reading(consumption_kwh=1.0), imputer)
    second = reading_to_curated_row(_reading(consumption_kwh=None), imputer)

    assert first["imputation_methods"] is None
    assert second["consumption_kwh"] == 1.0
    assert second["imputation_methods"] == "forward_fill"


def test_in_range_filters_by_start_and_end():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)

    assert _in_range("2023-12-31T23:59:59", start, end) is False
    assert _in_range("2024-01-01T00:00:00", start, end) is True
    assert _in_range("2024-01-02T00:00:00", start, end) is False


def test_backfill_reads_raw_objects_and_upserts_curated_rows():
    raw_reader = Mock()
    raw_reader.list_object_keys.return_value = [
        "SITE001/2024/01/01/00/00.json",
        "SITE001/2024/01/01/00/01.json",
    ]
    raw_reader.read_object.side_effect = [
        _reading(timestamp="2024-01-01T00:00:00", consumption_kwh=1.0),
        _reading(timestamp="2024-01-01T00:01:00", consumption_kwh=2.0),
    ]
    curated_writer = Mock()
    curated_writer.upsert_many.return_value = 2

    BackfillCuratedFromRawJob(
        raw_reader=raw_reader,
        curated_writer=curated_writer,
        batch_size=10,
    ).run()

    curated_writer.upsert_many.assert_called_once()
    rows = curated_writer.upsert_many.call_args[0][0]
    assert len(rows) == 2
    assert rows[0]["site_id"] == "SITE001"
    assert rows[1]["consumption_kwh"] == 2.0


def test_backfill_skips_objects_outside_date_window():
    raw_reader = Mock()
    raw_reader.list_object_keys.return_value = ["SITE001/2024/01/01/00/00.json"]
    raw_reader.read_object.return_value = _reading(timestamp="2025-01-01T00:00:00")
    curated_writer = Mock()

    BackfillCuratedFromRawJob(
        raw_reader=raw_reader,
        curated_writer=curated_writer,
        start_time="2024-01-01T00:00:00",
        end_time="2024-12-31T23:59:59",
    ).run()

    curated_writer.upsert_many.assert_not_called()


def test_build_parser_parses_backfill_curated_args():
    args = build_parser().parse_args(
        [
            "--prefix",
            "SITE001/",
            "--start",
            "2024-01-01T00:00:00",
            "--end",
            "2026-01-01T00:00:00",
            "--batch-size",
            "100",
        ]
    )

    assert args.prefix == "SITE001/"
    assert args.start == "2024-01-01T00:00:00"
    assert args.end == "2026-01-01T00:00:00"
    assert args.batch_size == 100
