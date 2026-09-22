import pandas as pd

from infrastructure.ml.state.features import RAW_COLUMNS, SENSOR_COLUMNS, build_features
from infrastructure.ml.state.trainer import train_model
from infrastructure.training_data import (
    MockStateTrainingDataReader,
    PostgresStateTrainingDataReader,
    create_state_training_data_reader,
)


def test_mock_state_training_data_reader_returns_expected_columns():
    reader = MockStateTrainingDataReader()
    df = reader.fetch_training_data()

    assert list(df.columns) == RAW_COLUMNS
    assert len(df) >= 20
    assert df["data_quality"].notna().all()


def test_mock_state_training_data_reader_feeds_training_pipeline():
    df = MockStateTrainingDataReader().fetch_training_data()
    x, y = build_features(df)
    result = train_model(df, test_size=0.25, random_state=42)

    assert len(x) == len(y)
    assert 0.0 <= result.accuracy <= 1.0


def test_create_state_training_data_reader_defaults_to_mock():
    reader = create_state_training_data_reader()
    df = reader.fetch_training_data()

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == RAW_COLUMNS


def test_postgres_state_training_data_reader_fetch(monkeypatch):
    expected = pd.DataFrame(
        {
            "site_id": ["SITE001"],
            "timestamp": ["2026-09-07T00:00:00"],
            "data_quality": ["good"],
            **{name: [1.0] for name in SENSOR_COLUMNS},
        }
    )

    def fake_read_sql(_stmt, _engine):
        return expected.copy()

    monkeypatch.setattr(
        "infrastructure.training_data.state.postgres_reader.pd.read_sql",
        fake_read_sql,
    )

    reader = PostgresStateTrainingDataReader("postgresql+psycopg://test")
    df = reader.fetch_training_data()

    assert list(df.columns) == RAW_COLUMNS
    assert len(df) == 1
    assert df.loc[0, "data_quality"] == "good"


def test_postgres_state_training_data_reader_query_filters_on_data_quality():
    from sqlalchemy.dialects import postgresql

    from db_schema.models import ReadingCurated
    from sqlalchemy import select

    stmt = (
        select(
            ReadingCurated.site_id,
            ReadingCurated.timestamp,
            ReadingCurated.data_quality,
            *(getattr(ReadingCurated, name) for name in SENSOR_COLUMNS),
        )
        .where(ReadingCurated.data_quality.is_not(None))
        .order_by(ReadingCurated.timestamp)
    )
    sql = str(stmt.compile(dialect=postgresql.dialect()))

    assert "data_quality" in sql
    assert all(name in sql for name in SENSOR_COLUMNS)
    assert "consumption_kwh" not in sql
