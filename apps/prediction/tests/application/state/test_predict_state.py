from datetime import datetime, timezone

import pytest

from application.state.predict_state import StateModelNotLoadedError, predict_state
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
    assert set(result.sensors.values()) <= {"on", "off"}


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
