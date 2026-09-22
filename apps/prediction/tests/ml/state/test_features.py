import pandas as pd
import pytest

from infrastructure.ml.state.features import (
    FEATURE_COLUMNS,
    RAW_COLUMNS,
    SENSOR_COLUMNS,
    TARGET_COLUMN,
    aggregate_hourly,
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


def _reading(site_id, timestamp, off=()):
    row = {"site_id": site_id, "timestamp": timestamp, "data_quality": "good"}
    for name in SENSOR_COLUMNS:
        row[name] = None if name in off else 1.0
    return row


def test_aggregate_hourly_keeps_sensor_on_with_a_single_isolated_blip():
    # 1 relevé "off" sur 12 (~8%) : sous le seuil (10%), ignoré comme bruit -
    # cadence dense (~1 lecture toutes les 5 min) observée en réel (voir
    # docs/state-model.md, section Limites).
    df = pd.DataFrame(
        [_reading("SITE001", f"2026-09-22T14:{minute:02d}:00") for minute in range(0, 60, 5)]
    )
    df.loc[1, "humidity_percent"] = None  # une seule lecture off sur 12

    hourly = aggregate_hourly(df)

    assert len(hourly) == 1
    assert hourly.loc[0, "humidity_percent"] == 1.0
    assert hourly.loc[0, "data_quality"] == "good"


def test_aggregate_hourly_marks_sensor_off_with_repeated_failures():
    # 3 relevés "off" sur 12 (25%, >= 10%) dans la même heure - ex. une
    # coupure réseau de 3 lectures consécutives (~15 min à cette cadence).
    df = pd.DataFrame(
        [_reading("SITE001", f"2026-09-22T14:{minute:02d}:00") for minute in range(0, 60, 5)]
    )
    df.loc[[0, 1, 2], "humidity_percent"] = None

    hourly = aggregate_hourly(df)

    assert len(hourly) == 1
    assert hourly.loc[0, "humidity_percent"] is None
    assert hourly.loc[0, "data_quality"] == "off"


def test_aggregate_hourly_groups_by_site_and_hour():
    df = pd.DataFrame(
        [
            _reading("SITE001", "2026-09-22T14:05:00"),
            _reading("SITE001", "2026-09-22T15:05:00"),
            _reading("SITE002", "2026-09-22T14:05:00"),
        ]
    )

    hourly = aggregate_hourly(df)

    assert len(hourly) == 3
    assert list(hourly.columns) == RAW_COLUMNS


def test_aggregate_hourly_respects_custom_threshold():
    # 1 relevé "off" sur 2 = 50%.
    df = pd.DataFrame(
        [
            _reading("SITE001", "2026-09-22T14:00:00", off=["humidity_percent"]),
            _reading("SITE001", "2026-09-22T14:30:00"),
        ]
    )

    assert aggregate_hourly(df, min_off_ratio=0.4).loc[0, "humidity_percent"] is None
    assert aggregate_hourly(df, min_off_ratio=0.6).loc[0, "humidity_percent"] == 1.0
