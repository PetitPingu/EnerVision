from datetime import datetime, timezone

import pytest

from application.predict import (
    InvalidIntervalError,
    InvalidPredictionRangeError,
    ModelNotLoadedError,
    predict,
    predict_range,
)
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


def test_predict_range_returns_minute_by_minute_predictions(monkeypatch):
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
            return publish.training.pipeline, publish.metadata

    start = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 17, 8, 2, tzinfo=timezone.utc)

    result = predict_range(
        model_store=FakeStore(),
        model_name="energy-consumption",
        site_id="SITE001",
        start_time=start,
        end_time=end,
    )

    assert result.site_id == "SITE001"
    assert result.start_time == start
    assert result.end_time == end
    assert result.model_version == "2026-09-16T14-30-00Z"
    assert len(result.predictions) == 3
    assert [point.target_timestamp for point in result.predictions] == [
        datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 17, 8, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 17, 8, 2, tzinfo=timezone.utc),
    ]
    assert all(point.predicted_consumption_kwh >= 0 for point in result.predictions)


def test_predict_range_returns_hourly_predictions_when_interval_is_hour(monkeypatch):
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
            return publish.training.pipeline, publish.metadata

    start = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)

    result = predict_range(
        model_store=FakeStore(),
        model_name="energy-consumption",
        site_id="SITE001",
        start_time=start,
        end_time=end,
        interval="hour",
    )

    assert result.interval == "hour"
    assert [point.target_timestamp for point in result.predictions] == [
        datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 17, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc),
    ]


def test_predict_range_raises_when_interval_is_invalid():
    start = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(InvalidIntervalError):
        predict_range(
            model_store=_BrokenStore(),
            model_name="energy-consumption",
            site_id="SITE001",
            start_time=start,
            end_time=end,
            interval="day",
        )


def test_predict_range_raises_when_start_after_end():
    start = datetime(2026, 9, 17, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)

    with pytest.raises(InvalidPredictionRangeError, match="start_time must be before end_time"):
        predict_range(
            model_store=_BrokenStore(),
            model_name="energy-consumption",
            site_id="SITE001",
            start_time=start,
            end_time=end,
        )


def test_predict_range_raises_when_range_exceeds_limit():
    start = datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 17, 0, 2, tzinfo=timezone.utc)

    with pytest.raises(
        InvalidPredictionRangeError,
        match="range exceeds maximum of 2 points at interval 'minute'",
    ):
        predict_range(
            model_store=_BrokenStore(),
            model_name="energy-consumption",
            site_id="SITE001",
            start_time=start,
            end_time=end,
            max_minutes=2,
        )


class _BrokenStore:
    def save(self, pipeline, metadata):
        raise NotImplementedError

    def load_latest(self, model_name):
        raise NotImplementedError


class _RecordingStore:
    def save(self, pipeline, metadata):
        return f"{metadata.model_name}/{metadata.trained_at}"

    def load_latest(self, model_name):
        raise NotImplementedError
