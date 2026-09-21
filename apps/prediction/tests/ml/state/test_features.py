import pandas as pd
import pytest

from infrastructure.ml.state.features import (
    FEATURE_COLUMNS,
    SENSOR_COLUMNS,
    TARGET_COLUMN,
    build_features,
    build_sensor_targets,
)


def _with_sensors(df, off=()):
    for name in SENSOR_COLUMNS:
        df[name] = [None if name in off else 1.0] * len(df)
    return df


def test_build_features():
    df = pd.DataFrame(
        {
            "site_id": ["SITE001", "SITE002", "SITE001"],
            "timestamp": [
                "2024-06-15T14:00:00",
                "2024-06-16T09:30:00",
                "2024-06-15T18:00:00",
            ],
            "data_quality": ["good", "partial", None],
        }
    )
    df = _with_sensors(df)
    x, y = build_features(df)

    assert list(x.columns) == FEATURE_COLUMNS
    assert len(x) == 2
    assert y.iloc[0] == "good"
    assert x.loc[0, "site_id"] == "SITE001"
    assert x.loc[0, "hour"] == 14
    assert x.loc[0, "minute"] == 0
    assert TARGET_COLUMN not in x.columns


def test_build_features_raises_on_missing_columns():
    df = pd.DataFrame({"site_id": ["SITE001"]})

    with pytest.raises(ValueError):
        build_features(df)


def test_build_sensor_targets_marks_null_measures_as_off():
    df = pd.DataFrame(
        {
            "site_id": ["SITE001", "SITE002", "SITE003"],
            "timestamp": ["2024-06-15T14:00:00"] * 3,
            "data_quality": ["good", "partial", None],
        }
    )
    df = _with_sensors(df)
    df.loc[1, "humidity_percent"] = None

    targets = build_sensor_targets(df)

    assert list(targets.columns) == SENSOR_COLUMNS
    assert len(targets) == 2  # la ligne sans data_quality est exclue, comme build_features
    assert targets.loc[0].tolist() == [1, 1, 1, 1, 1, 1]
    assert targets.loc[1, "humidity_percent"] == 0
    assert targets.loc[1].sum() == 5
