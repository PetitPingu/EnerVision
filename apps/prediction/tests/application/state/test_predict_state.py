from datetime import datetime, timezone

import pytest

from application.state.predict_state import (
    StateModelNotLoadedError,
    derive_state,
    predict_state,
)
from application.state.train_and_publish_state import train_and_publish_state
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
    assert result.predicted_state in ("good", "partial", "degraded", "critical")


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


def test_predict_state_returns_on_off_per_sensor_and_derived_state(monkeypatch):
    from infrastructure.ml.state.features import SENSOR_COLUMNS

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

    result = predict_state(
        model_store=FakeStore(),
        model_name="sensor-state-model",
        site_id="SITE001",
        target_timestamp=datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc),
    )

    assert list(result.sensors) == SENSOR_COLUMNS
    assert set(result.sensors.values()) <= {"on", "off"}
    assert result.predicted_state == derive_state(list(result.sensors.values()).count("off"))


@pytest.mark.parametrize(
    ("off_count", "expected"),
    [
        (0, "good"),
        (1, "partial"),
        (2, "partial"),
        (3, "degraded"),
        (4, "critical"),
        (6, "critical"),
    ],
)
def test_derive_state_from_off_sensor_count(off_count, expected):
    assert derive_state(off_count) == expected


def test_predict_state_supports_legacy_model_predicting_state_directly():
    from application.ports import SavedModelMetadata

    class LegacyPipeline:
        def predict(self, _x):
            return ["good"]

    class FakeStore:
        def load_latest(self, model_name):
            metadata = SavedModelMetadata(
                model_name=model_name,
                trained_at="2026-09-01T00-00-00Z",
                metrics={"accuracy": 1.0},
                train_size=1,
                test_size=1,
                features=("site_id", "hour", "minute"),
            )
            return LegacyPipeline(), metadata

    result = predict_state(
        model_store=FakeStore(),
        model_name="sensor-state-model",
        site_id="SITE001",
        target_timestamp=datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc),
    )

    assert result.predicted_state == "good"
    assert result.sensors == {}
