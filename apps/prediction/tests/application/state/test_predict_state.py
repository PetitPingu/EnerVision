from datetime import datetime, timedelta, timezone

import pytest

from application.state.predict_state import (
    InvalidStateRangeError,
    StateModelNotLoadedError,
    predict_state,
    predict_state_range,
)
from application.state.train_and_publish_state import train_and_publish_state
from infrastructure.ml.state.features import SENSOR_COLUMNS
from infrastructure.training_data import MockStateTrainingDataReader


def test_predict_state_returns_prediction_from_latest_model(monkeypatch):
    monkeypatch.setattr(
        "application.state.train_and_publish_state.utc_version_timestamp",
        lambda: "2026-09-16T14-30-00Z",
    )

    publish = train_and_publish_state(
        data_reader=MockStateTrainingDataReader(),
        model_store=_RecordingStore(),
        model_name="sensor-state-model",
    )

    class FakeStore:
        def save(self, pipeline, metadata):
            raise NotImplementedError

        def load_latest(self, model_name):
            assert model_name == "sensor-state-model"
            return publish.training.pipeline, publish.metadata

    target = datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc)

    result = predict_state(
        model_store=FakeStore(),
        model_name="sensor-state-model",
        site_id="SITE001",
        target_timestamp=target,
    )

    assert result.site_id == "SITE001"
    assert result.target_timestamp == target
    assert result.model_version == "2026-09-16T14-30-00Z"
    assert list(result.sensors) == SENSOR_COLUMNS
    assert {p.state for p in result.sensors.values()} <= {"on", "off"}
    assert all(0.0 <= p.confidence <= 1.0 for p in result.sensors.values())


def test_predict_state_range_returns_one_point_per_hour(monkeypatch):
    monkeypatch.setattr(
        "application.state.train_and_publish_state.utc_version_timestamp",
        lambda: "2026-09-16T14-30-00Z",
    )

    publish = train_and_publish_state(
        data_reader=MockStateTrainingDataReader(),
        model_store=_RecordingStore(),
        model_name="sensor-state-model",
    )

    class FakeStore:
        def load_latest(self, model_name):
            return publish.training.pipeline, publish.metadata

    start = datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)

    result = predict_state_range(
        model_store=FakeStore(),
        model_name="sensor-state-model",
        site_id="SITE001",
        start_time=start,
        hours=24,
    )

    assert result.site_id == "SITE001"
    assert result.hours == 24
    assert len(result.points) == 24
    assert result.points[0].target_timestamp == start + timedelta(hours=1)
    assert result.points[-1].target_timestamp == start + timedelta(hours=24)
    assert list(result.points[0].sensors) == SENSOR_COLUMNS


def test_predict_state_range_rejects_invalid_hours():
    class FakeStore:
        def load_latest(self, model_name):
            raise NotImplementedError

    with pytest.raises(InvalidStateRangeError):
        predict_state_range(
            model_store=FakeStore(),
            model_name="sensor-state-model",
            site_id="SITE001",
            start_time=datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc),
            hours=0,
        )


def test_predict_state_raises_when_model_expects_a_removed_feature():
    # Modèle entraîné avant le retrait de "minute" (aggregate_hourly) :
    # son ColumnTransformer interne attend une colonne que le code actuel
    # ne fournit plus. Doit être traité comme un modèle à réentraîner
    # (503), pas planter (500) - voir predict_state.py, _predict_sensors.
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.multioutput import MultiOutputClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    from application.ports import SavedModelMetadata

    # Reproduit la forme d'un pipeline entraîné avant le retrait de
    # "minute" (create_model_pipeline() reflète déjà le nouveau schéma,
    # on ne peut pas l'utiliser pour simuler l'ancien).
    old_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                ColumnTransformer(
                    transformers=[
                        ("cat", OneHotEncoder(handle_unknown="ignore"), ["site_id"]),
                        ("num", "passthrough", ["hour", "minute"]),
                    ],
                ),
            ),
            ("model", MultiOutputClassifier(RandomForestClassifier(random_state=42))),
        ],
    )
    old_x = pd.DataFrame(
        {"site_id": ["SITE001", "SITE002"], "hour": [10, 11], "minute": [0, 30]}
    )
    old_sensors = pd.DataFrame({name: [1, 0] for name in SENSOR_COLUMNS})
    old_pipeline.fit(old_x, old_sensors.to_numpy())

    class FakeStore:
        def load_latest(self, model_name):
            metadata = SavedModelMetadata(
                model_name=model_name,
                trained_at="2026-09-01T00-00-00Z",
                metrics={"accuracy": 0.9},
                train_size=2,
                test_size=1,
                features=("site_id", "hour", "minute"),
            )
            return old_pipeline, metadata

    with pytest.raises(StateModelNotLoadedError):
        predict_state(
            model_store=FakeStore(),
            model_name="sensor-state-model",
            site_id="SITE001",
            target_timestamp=datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc),
        )


def test_predict_state_raises_when_model_unavailable():
    class BrokenStore:
        def save(self, pipeline, metadata):
            raise NotImplementedError

        def load_latest(self, model_name):
            raise FileNotFoundError("latest/model.joblib")

    with pytest.raises(StateModelNotLoadedError):
        predict_state(
            model_store=BrokenStore(),
            model_name="sensor-state-model",
            site_id="SITE001",
            target_timestamp=datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc),
        )


class _RecordingStore:
    def save(self, pipeline, metadata):
        return f"{metadata.model_name}/{metadata.trained_at}"

    def load_latest(self, model_name):
        raise NotImplementedError
