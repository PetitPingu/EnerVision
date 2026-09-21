from datetime import datetime, timezone

from fastapi.testclient import TestClient

from application.consumption.predict import (
    InvalidPredictionRangeError,
    ModelNotLoadedError,
    PredictionPoint,
    PredictionRangeResult,
    PredictionResult,
)
from application.state.predict_state import StateModelNotLoadedError, StatePredictionResult
from presentation.api import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "prediction"
    assert "/health" in body["endpoints"]
    assert "/predict" in body["endpoints"]
    assert "/predict/range" in body["endpoints"]
    assert "/predict/state" in body["endpoints"]


def test_predict_returns_prediction(monkeypatch):
    target = datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc)

    def fake_predict(**_kwargs):
        return PredictionResult(
            site_id="SITE001",
            target_timestamp=target,
            predicted_consumption_kwh=123.45,
            model_version="2026-09-16T14-30-00Z",
        )

    monkeypatch.setattr("presentation.api.run_predict", fake_predict)
    logged_calls = []
    monkeypatch.setattr(
        "presentation.api.PredictionLogWriter",
        lambda: _FakePredictionLogWriter(logged_calls),
    )

    client = TestClient(app)
    response = client.get(
        "/predict",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "site_id": "SITE001",
        "target_timestamp": "2026-09-17T14:30:00Z",
        "predicted_consumption_kwh": 123.45,
        "model_version": "2026-09-16T14-30-00Z",
    }
    assert logged_calls == [
        {
            "site_id": "SITE001",
            "target_timestamp": target,
            "predicted_consumption_kwh": 123.45,
            "model_version": "2026-09-16T14-30-00Z",
        }
    ]


def test_predict_succeeds_even_if_predictions_log_write_fails(monkeypatch):
    target = datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc)

    def fake_predict(**_kwargs):
        return PredictionResult(
            site_id="SITE001",
            target_timestamp=target,
            predicted_consumption_kwh=123.45,
            model_version="2026-09-16T14-30-00Z",
        )

    monkeypatch.setattr("presentation.api.run_predict", fake_predict)

    class _BrokenWriter:
        def log(self, **_kwargs):
            raise RuntimeError("Postgres indisponible")

    monkeypatch.setattr("presentation.api.PredictionLogWriter", _BrokenWriter)

    client = TestClient(app)
    response = client.get(
        "/predict",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["predicted_consumption_kwh"] == 123.45


class _FakePredictionLogWriter:
    """Capture les appels à .log() sans toucher Postgres."""

    def __init__(self, calls: list):
        self._calls = calls

    def log(self, **kwargs):
        self._calls.append(kwargs)


def test_predict_returns_503_when_model_not_loaded(monkeypatch):
    def fake_predict(**_kwargs):
        raise ModelNotLoadedError("missing model")

    monkeypatch.setattr("presentation.api.run_predict", fake_predict)

    client = TestClient(app)
    response = client.get(
        "/predict",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "model not loaded"}


def test_predict_range_returns_predictions(monkeypatch):
    start = datetime(2026, 9, 17, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 17, 8, 1, tzinfo=timezone.utc)

    def fake_predict_range(**_kwargs):
        return PredictionRangeResult(
            site_id="SITE001",
            start_time=start,
            end_time=end,
            interval="minute",
            model_version="2026-09-16T14-30-00Z",
            predictions=(
                PredictionPoint(
                    target_timestamp=start,
                    predicted_consumption_kwh=100.0,
                ),
                PredictionPoint(
                    target_timestamp=end,
                    predicted_consumption_kwh=101.0,
                ),
            ),
        )

    monkeypatch.setattr("presentation.api.run_predict_range", fake_predict_range)

    client = TestClient(app)
    response = client.get(
        "/predict/range",
        params={
            "site_id": "SITE001",
            "start_time": "2026-09-17T08:00:00Z",
            "end_time": "2026-09-17T08:01:00Z",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "site_id": "SITE001",
        "start_time": "2026-09-17T08:00:00Z",
        "end_time": "2026-09-17T08:01:00Z",
        "interval": "minute",
        "model_version": "2026-09-16T14-30-00Z",
        "count": 2,
        "predictions": [
            {
                "target_timestamp": "2026-09-17T08:00:00Z",
                "predicted_consumption_kwh": 100.0,
            },
            {
                "target_timestamp": "2026-09-17T08:01:00Z",
                "predicted_consumption_kwh": 101.0,
            },
        ],
    }


def test_predict_range_returns_422_for_invalid_range(monkeypatch):
    def fake_predict_range(**_kwargs):
        raise InvalidPredictionRangeError("start_time must be before end_time")

    monkeypatch.setattr("presentation.api.run_predict_range", fake_predict_range)

    client = TestClient(app)
    response = client.get(
        "/predict/range",
        params={
            "site_id": "SITE001",
            "start_time": "2026-09-17T10:00:00Z",
            "end_time": "2026-09-17T08:00:00Z",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "start_time must be before end_time"}


def test_predict_range_returns_503_when_model_not_loaded(monkeypatch):
    def fake_predict_range(**_kwargs):
        raise ModelNotLoadedError("missing model")

    monkeypatch.setattr("presentation.api.run_predict_range", fake_predict_range)

    client = TestClient(app)
    response = client.get(
        "/predict/range",
        params={
            "site_id": "SITE001",
            "start_time": "2026-09-17T08:00:00Z",
            "end_time": "2026-09-17T08:01:00Z",
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "model not loaded"}


def test_predict_returns_422_for_invalid_timestamp():
    client = TestClient(app)
    response = client.get(
        "/predict",
        params={"site_id": "SITE001", "timestamp": "not-a-date"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "timestamp must be ISO8601"}


def test_predict_state_returns_prediction(monkeypatch):
    target = datetime(2026, 9, 17, 14, 30, tzinfo=timezone.utc)

    def fake_predict_state(**_kwargs):
        return StatePredictionResult(
            site_id="SITE001",
            target_timestamp=target,
            predicted_state="good",
            model_version="2026-09-16T14-30-00Z",
        )

    monkeypatch.setattr("presentation.api.run_predict_state", fake_predict_state)

    client = TestClient(app)
    response = client.get(
        "/predict/state",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "site_id": "SITE001",
        "target_timestamp": "2026-09-17T14:30:00Z",
        "predicted_state": "good",
        "model_version": "2026-09-16T14-30-00Z",
    }


def test_predict_state_returns_503_when_model_not_loaded(monkeypatch):
    def fake_predict_state(**_kwargs):
        raise StateModelNotLoadedError("missing model")

    monkeypatch.setattr("presentation.api.run_predict_state", fake_predict_state)

    client = TestClient(app)
    response = client.get(
        "/predict/state",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "state model not loaded"}


def test_predict_state_returns_422_for_invalid_timestamp():
    client = TestClient(app)
    response = client.get(
        "/predict/state",
        params={"site_id": "SITE001", "timestamp": "not-a-date"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "timestamp must be ISO8601"}
