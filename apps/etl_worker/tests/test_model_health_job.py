from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from application.model_health_job import ModelHealthJob
from domain.model_health import (
    DistributionStats,
    MIN_HORIZON_SAMPLE_SIZE,
    MIN_SAMPLE_SIZE,
    ReconciledPrediction,
)


def _reconciled(**overrides) -> ReconciledPrediction:
    # Horodatages relatifs à l'instant du test, pas figés : compute_mae_24h
    # (voir application/model_health_job.py) filtre sur datetime.now(timezone.utc),
    # une date en dur finit hors fenêtre dès que le temps réel avance.
    now = datetime.now(timezone.utc)
    data = {
        "site_id": "SITE001",
        "target_timestamp": now - timedelta(minutes=30),
        "predicted_consumption_kwh": 100.0,
        "actual_consumption_kwh": 90.0,
        "model_version": "2026-09-16T14-30-00Z",
        "generated_at": now - timedelta(hours=1),
        **overrides,
    }
    return ReconciledPrediction(**data)


def test_run_publishes_mae_and_drift_when_reconciled_predictions_exist(monkeypatch):
    reader = Mock()
    reader.fetch_reconciled_predictions.return_value = [_reconciled()]
    reader.fetch_consumption_stats.return_value = DistributionStats(
        mean=100.0, stddev=10.0, count=MIN_SAMPLE_SIZE
    )

    published = {}
    monkeypatch.setattr(
        "application.model_health_job.publish_model_health",
        lambda mae, drift, versions, horizon, mae_7d: published.update(
            {"mae": mae, "drift": drift, "versions": versions, "horizon": horizon, "mae_7d": mae_7d}
        ),
    )

    job = ModelHealthJob(reader=reader)
    job.run()

    assert published["mae"] == {"SITE001": 10.0}
    assert published["versions"] == {"SITE001": "2026-09-16T14-30-00Z"}
    assert published["drift"] == {"SITE001": 0.0}
    assert published["horizon"] == {}  # un seul point rapproché, sous MIN_HORIZON_SAMPLE_SIZE
    assert published["mae_7d"] == {"SITE001": 10.0}


def test_run_does_not_raise_when_postgres_is_unreachable(monkeypatch):
    reader = Mock()
    reader.fetch_reconciled_predictions.side_effect = RuntimeError("Postgres indisponible")

    monkeypatch.setattr(
        "application.model_health_job.publish_model_health",
        Mock(side_effect=AssertionError("ne doit pas être appelé")),
    )

    job = ModelHealthJob(reader=reader)

    job.run()  # ne doit pas lever


def test_run_skips_drift_when_model_version_is_unparseable(monkeypatch):
    reader = Mock()
    reader.fetch_reconciled_predictions.return_value = [
        _reconciled(model_version="not-a-version")
    ]

    published = {}
    monkeypatch.setattr(
        "application.model_health_job.publish_model_health",
        lambda mae, drift, versions, horizon, mae_7d: published.update(
            {"mae": mae, "drift": drift, "versions": versions, "horizon": horizon, "mae_7d": mae_7d}
        ),
    )

    job = ModelHealthJob(reader=reader)
    job.run()

    assert published["drift"] == {}
    reader.fetch_consumption_stats.assert_not_called()


def test_run_publishes_mae_by_horizon_when_enough_samples_exist(monkeypatch):
    now = datetime.now(timezone.utc)
    reader = Mock()
    reader.fetch_reconciled_predictions.return_value = [
        _reconciled(
            generated_at=now - timedelta(minutes=30),
            target_timestamp=now,
            model_version="not-a-version",  # isole ce test du calcul de drift
        )
        for _ in range(MIN_HORIZON_SAMPLE_SIZE)
    ]

    published = {}
    monkeypatch.setattr(
        "application.model_health_job.publish_model_health",
        lambda mae, drift, versions, horizon, mae_7d: published.update({"horizon": horizon}),
    )

    job = ModelHealthJob(reader=reader)
    job.run()

    assert published["horizon"] == {"SITE001": {"0-1h": 10.0}}
    # Une seule requête de rapprochement, avec une fenêtre large (pas 24h) :
    # sert à la fois au calcul 24h glissant et au profil par horizon.
    reader.fetch_reconciled_predictions.assert_called_once()
    called_since = reader.fetch_reconciled_predictions.call_args.kwargs["since"]
    assert called_since < datetime.now(timezone.utc) - timedelta(days=20)
