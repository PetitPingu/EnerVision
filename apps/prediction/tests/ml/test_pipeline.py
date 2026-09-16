import pandas as pd

from infrastructure.ml.features import build_features
from infrastructure.ml.pipeline import create_model_pipeline


def _sample_raw_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "site_id": ["SITE001", "SITE002", "SITE001", "SITE002"],
            "timestamp": [
                "2024-06-15T08:00:00",
                "2024-06-15T09:00:00",
                "2024-06-15T14:00:00",
                "2024-06-15T15:30:00",
            ],
            "consumption_kwh": [10.0, 20.0, 15.0, 25.0],
        }
    )


def test_create_model_pipeline_fit_and_predict():
    x, y = build_features(_sample_raw_df())
    pipeline = create_model_pipeline()

    pipeline.fit(x, y)
    predictions = pipeline.predict(x)

    assert len(predictions) == len(y)
    assert all(pred >= 0 for pred in predictions)
