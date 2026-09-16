import pandas as pd

from infrastructure.ml.features import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_features,
    extract_temporal_features,
)


def test_extract_temporal_features():
    df = pd.DataFrame({"timestamp": ["2024-06-15T14:32:00"]})
    result = extract_temporal_features(df)

    assert result.loc[0, "hour"] == 14
    assert result.loc[0, "minute"] == 32


def test_extract_temporal_features_mixed_iso8601_formats():
    df = pd.DataFrame(
        {
            "timestamp": [
                "2026-09-07T00:00:00",
                "2026-09-07T00:40:33.802817",
            ]
        }
    )
    result = extract_temporal_features(df)

    assert result.loc[0, "hour"] == 0
    assert result.loc[0, "minute"] == 0
    assert result.loc[1, "hour"] == 0
    assert result.loc[1, "minute"] == 40


def test_build_features():
    df = pd.DataFrame(
        {
            "site_id": ["SITE001", "SITE002", "SITE001"],
            "timestamp": [
                "2024-06-15T14:00:00",
                "2024-06-16T09:30:00",
                "2024-06-15T18:00:00",
            ],
            "consumption_kwh": [12.5, 8.3, None],
        }
    )
    x, y = build_features(df)

    assert list(x.columns) == FEATURE_COLUMNS
    assert len(x) == 2
    assert y.iloc[0] == 12.5
    assert x.loc[0, "site_id"] == "SITE001"
    assert x.loc[0, "hour"] == 14
    assert x.loc[0, "minute"] == 0
    assert TARGET_COLUMN not in x.columns
