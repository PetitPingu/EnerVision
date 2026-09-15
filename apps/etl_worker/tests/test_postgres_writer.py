from unittest.mock import MagicMock, patch

from infrastructure.postgres_writer import ReadingsRawWriter
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


def test_insert_returns_true_and_uses_on_conflict_do_nothing():
    conn, cursor = _mock_connect(rowcount=1)
    reading = _reading()

    with patch("infrastructure.postgres_writer.psycopg2.connect", return_value=conn):
        writer = ReadingsRawWriter(dsn="postgresql://fake")
        inserted = writer.insert(reading)

    assert inserted is True
    sql = cursor.execute.call_args[0][0]
    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql
    params = cursor.execute.call_args[0][1]
    assert params[0] == "SITE001"
    assert params[-1] == "good"
    conn.close.assert_called_once()


def test_insert_returns_false_on_conflict():
    conn, cursor = _mock_connect(rowcount=0)
    reading = _reading()

    with patch("infrastructure.postgres_writer.psycopg2.connect", return_value=conn):
        writer = ReadingsRawWriter(dsn="postgresql://fake")
        inserted = writer.insert(reading)

    assert inserted is False


def test_insert_closes_connection_even_on_error():
    conn = MagicMock()
    conn.__enter__.side_effect = RuntimeError("boom")

    with patch("infrastructure.postgres_writer.psycopg2.connect", return_value=conn):
        writer = ReadingsRawWriter(dsn="postgresql://fake")
        try:
            writer.insert(_reading())
        except RuntimeError:
            pass

    conn.close.assert_called_once()
