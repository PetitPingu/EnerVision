from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

from infrastructure.curated_writer import CuratedWriter


def _row(**overrides) -> dict:
    data = {
        "site_id": "SITE001",
        "timestamp": "2026-09-16T10:00:00+00:00",
        "site_type": "office",
        "consumption_kw": 10.0,
        "consumption_kw_imputed": 10.0,
        "imputation_methods": {},
        "null_reasons": [],
        "data_quality": "good",
        **overrides,
    }
    return data


def test_upsert_many_with_empty_rows_does_not_touch_the_engine():
    engine = Mock()
    writer = CuratedWriter(engine=engine)

    written = writer.upsert_many([])

    assert written == 0
    engine.begin.assert_not_called()


def test_upsert_many_executes_once_and_returns_row_count():
    engine = MagicMock()
    conn = engine.begin.return_value.__enter__.return_value
    writer = CuratedWriter(engine=engine)

    written = writer.upsert_many([_row(), _row(site_id="SITE002")])

    assert written == 2
    conn.execute.assert_called_once()


def test_to_row_values_converts_timestamp_string_to_datetime():
    values = CuratedWriter._to_row_values(_row())

    assert values["timestamp"] == datetime(2026, 9, 16, 10, 0, tzinfo=timezone.utc)


def test_to_row_values_defaults_naive_timestamp_to_utc():
    values = CuratedWriter._to_row_values(_row(timestamp="2026-09-16T10:00:00"))

    assert values["timestamp"] == datetime(2026, 9, 16, 10, 0, tzinfo=timezone.utc)


def test_to_row_values_drops_keys_that_are_not_curated_columns():
    values = CuratedWriter._to_row_values(_row(raw_payload=b"{}", something_else="ignored"))

    assert "raw_payload" not in values
    assert "something_else" not in values
    assert values["site_id"] == "SITE001"
