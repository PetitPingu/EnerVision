import pandas as pd

from infrastructure.ml.consumption.features import build_features
from infrastructure.ml.consumption.trainer import train_model


def _sample_raw_df() -> pd.DataFrame:
    rows = []
    for i in range(20):
        rows.append(
            {
                "site_id": f"SITE00{(i % 2) + 1}",
                "timestamp": f"2024-06-15T{8 + (i % 10):02d}:00:00",
                "consumption_kwh": 10.0 + i,
                "temperature_celsius": 18.0 + (i % 5),
                "site_type": "industrial" if i % 2 == 0 else "commercial",
            }
        )
    return pd.DataFrame(rows)


def test_train_model_returns_metrics_and_fitted_pipeline():
    result = train_model(_sample_raw_df(), test_size=0.25, random_state=42)

    assert result.train_size > 0
    assert result.test_size > 0
    assert result.train_size + result.test_size == 20
    assert result.mae >= 0
    assert result.rmse >= 0

    x, _ = build_features(_sample_raw_df())
    predictions = result.pipeline.predict(x)
    assert len(predictions) == len(x)
