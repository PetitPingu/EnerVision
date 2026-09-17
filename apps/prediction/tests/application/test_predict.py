from datetime import datetime, timezone

import pytest

from application.predict import ModelNotLoadedError, predict
from application.train_and_publish import train_and_publish
from infrastructure.training_data import MockTrainingDataReader


def test_predict_returns_prediction_from_latest_model(monkeypatch):
    monkeypatch.setattr(
        "application.train_and_publish.utc_version_timestamp",
        lambda: "2026-09-16T14-30-00Z",
    )

    publish = train_and_publish(
        data_reader=MockTrainingDataReader(),
        model_store=_RecordingStore(),
        model_name="energy-consumption",
    )

    class FakeStore:
        def save(self, pipeline, metadata):
            raise NotImplementedError

        def load_latest(self, model_name):
            assert model_name == "energy-consumption"
            return publish.training.pipeline, publish.metadata

    target = datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc)

    result = predict(
        model_store=FakeStore(),
        model_name="energy-consumption",
        site_id="SITE001",
        target_timestamp=target,
    )

    assert result.site_id == "SITE001"
    assert result.target_timestamp == target
    assert result.model_version == "2026-09-16T14-30-00Z"
    assert result.predicted_consumption_kwh >= 0


def test_predict_raises_when_model_unavailable():
    class BrokenStore:
        def save(self, pipeline, metadata):
            raise NotImplementedError

        def load_latest(self, model_name):
            raise FileNotFoundError("latest/model.joblib")

    with pytest.raises(ModelNotLoadedError):
        predict(
            model_store=BrokenStore(),
            model_name="energy-consumption",
            site_id="SITE001",
            target_timestamp=datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc),
        )


class _RecordingStore:
    def save(self, pipeline, metadata):
        return f"{metadata.model_name}/{metadata.trained_at}"

    def load_latest(self, model_name):
        raise NotImplementedError
