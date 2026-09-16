import pandas as pd

from infrastructure.ml.features import RAW_COLUMNS, build_features
from infrastructure.ml.trainer import train_model
from infrastructure.training_data import (
    MockTrainingDataReader,
    PostgresTrainingDataReader,
    create_training_data_reader,
)


def test_mock_training_data_reader_returns_expected_columns():
    reader = MockTrainingDataReader()
    df = reader.fetch_training_data()

    assert list(df.columns) == RAW_COLUMNS
    assert len(df) >= 20
    assert df["consumption_kwh"].notna().all()


def test_mock_training_data_reader_feeds_training_pipeline():
    df = MockTrainingDataReader().fetch_training_data()
    x, y = build_features(df)
    result = train_model(df, test_size=0.25, random_state=42)

    assert len(x) == len(y)
    assert result.mae >= 0
    assert result.rmse >= 0


def test_create_training_data_reader_defaults_to_mock():
    reader = create_training_data_reader()
    df = reader.fetch_training_data()

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == RAW_COLUMNS


def test_postgres_training_data_reader_fetch(monkeypatch):
    expected = pd.DataFrame(
        {
            "site_id": ["SITE001"],
            "timestamp": ["2026-09-07T00:00:00"],
            "consumption_kwh": [100.0],
        }
    )

    def fake_read_sql(_stmt, _engine):
        return expected.copy()

    monkeypatch.setattr(
        "infrastructure.training_data.postgres_reader.pd.read_sql",
        fake_read_sql,
    )

    reader = PostgresTrainingDataReader("postgresql+psycopg://test")
    df = reader.fetch_training_data()

    assert list(df.columns) == RAW_COLUMNS
    assert len(df) == 1
    assert df.loc[0, "consumption_kwh"] == 100.0


def test_postgres_training_data_reader_query_has_no_data_quality_filter():
    from sqlalchemy.dialects import postgresql

    from db_schema.models import ReadingCurated
    from sqlalchemy import select

    stmt = (
        select(
            ReadingCurated.site_id,
            ReadingCurated.timestamp,
            ReadingCurated.consumption_kwh,
        )
        .where(ReadingCurated.consumption_kwh.is_not(None))
        .order_by(ReadingCurated.timestamp)
    )
    sql = str(stmt.compile(dialect=postgresql.dialect()))

    assert "consumption_kwh" in sql
    assert "data_quality" not in sql
