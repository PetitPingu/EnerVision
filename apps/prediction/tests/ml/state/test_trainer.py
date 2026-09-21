import pandas as pd

from infrastructure.ml.state.features import build_features
from infrastructure.ml.state.trainer import train_model
from infrastructure.training_data import MockStateTrainingDataReader


def _sample_raw_df() -> pd.DataFrame:
    return MockStateTrainingDataReader().fetch_training_data()


def test_train_model_returns_metrics_and_fitted_pipeline():
    result = train_model(_sample_raw_df(), test_size=0.25, random_state=42)

    assert result.train_size > 0
    assert result.test_size > 0
    assert result.train_size + result.test_size == len(_sample_raw_df())
    assert 0.0 <= result.accuracy <= 1.0
    assert 0.0 <= result.f1_macro <= 1.0

    x, _ = build_features(_sample_raw_df())
    predictions = result.pipeline.predict(x)
    assert len(predictions) == len(x)
