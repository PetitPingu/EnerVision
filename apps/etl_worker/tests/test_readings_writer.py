from unittest.mock import MagicMock, patch

from infrastructure.readings_writer import ReadingsWriter
from mockapi_client import EnergyReading


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
    return EnergyReading(**data)


def _mock_connect(rowcount: int):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = rowcount
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.__enter__.return_value = conn
    return conn, cursor


def test_insert_targets_enervision_readings_with_on_conflict_do_nothing():
    conn, cursor = _mock_connect(rowcount=1)

    with patch("infrastructure.readings_writer.psycopg2.connect", return_value=conn):
        writer = ReadingsWriter(dsn="postgresql://fake")
        inserted = writer.insert(_reading())

    assert inserted is True
    sql = cursor.execute.call_args[0][0]
    assert "enervision.readings" in sql
    assert "ON CONFLICT" in sql and "DO NOTHING" in sql
    conn.close.assert_called_once()


def test_insert_returns_false_on_conflict():
    conn, _ = _mock_connect(rowcount=0)

    with patch("infrastructure.readings_writer.psycopg2.connect", return_value=conn):
        writer = ReadingsWriter(dsn="postgresql://fake")
        inserted = writer.insert(_reading())

    assert inserted is False
