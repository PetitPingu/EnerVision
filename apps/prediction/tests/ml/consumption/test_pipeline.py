import pandas as pd

from infrastructure.ml.consumption.features import build_features
from infrastructure.ml.consumption.pipeline import SiteTypeWeekendExpander, create_model_pipeline


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
            "site_type": ["industrial", "commercial", "industrial", "commercial"],
        }
    )


def test_create_model_pipeline_fit_and_predict():
    x, y = build_features(_sample_raw_df())
    pipeline = create_model_pipeline()

    pipeline.fit(x, y)
    predictions = pipeline.predict(x)

    assert len(predictions) == len(y)
    assert all(pred >= 0 for pred in predictions)


def test_pipeline_predicts_without_site_type_column():
    """/predict n'envoie que site_id (voir application/consumption/predict.py)
    - le pipeline doit rester utilisable même sans colonne site_type en entrée."""
    x, y = build_features(_sample_raw_df())
    pipeline = create_model_pipeline()
    pipeline.fit(x, y)

    inference_input = pd.DataFrame(
        {
            "site_id": ["SITE001"],
            "hour": [10],
            "minute": [0],
            "day_of_week": [1],
        }
    )

    predictions = pipeline.predict(inference_input)

    assert len(predictions) == 1


def test_site_type_weekend_expander_derives_site_type_from_fitted_mapping():
    expander = SiteTypeWeekendExpander()
    expander.fit(
        pd.DataFrame(
            {
                "site_id": ["SITE001", "SITE002"],
                "site_type": ["industrial", "commercial"],
                "day_of_week": [0, 0],
            }
        )
    )

    result = expander.transform(
        pd.DataFrame(
            {
                "site_id": ["SITE001", "SITE002", "SITE999"],
                "day_of_week": [5, 1, 6],  # samedi, mardi, dimanche
            }
        )
    )

    assert list(result["site_type"]) == ["industrial", "commercial", "unknown"]
    assert list(result["is_weekend"]) == [1, 0, 1]
    assert list(result["site_type_weekend"]) == ["industrial_weekend", "commercial_weekday", "unknown_weekend"]
