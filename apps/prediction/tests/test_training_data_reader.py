import pandas as pd

from infrastructure.ml.features import RAW_COLUMNS, build_features
from infrastructure.mock_training_data_reader import MockTrainingDataReader
from infrastructure.ml.trainer import train_model
from infrastructure.training_data_factory import create_training_data_reader


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
