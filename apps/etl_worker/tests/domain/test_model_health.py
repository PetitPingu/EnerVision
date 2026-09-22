"""Tests de domain/model_health.py : calculs purs de MAE glissante et de
score de drift (docs/monitoring_model.md)."""

from datetime import datetime, timedelta, timezone

from domain.model_health import (
    ActualReading,
    DistributionStats,
    MIN_HORIZON_SAMPLE_SIZE,
    MIN_SAMPLE_SIZE,
    RawPrediction,
    ReconciledPrediction,
    compute_drift_score,
    compute_mae_24h,
    compute_mae_7d,
    compute_mae_by_horizon,
    horizon_bucket_label,
    latest_model_version_by_site,
    reconcile_predictions,
)

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _reconciled(**overrides) -> ReconciledPrediction:
    data = {
        "site_id": "SITE001",
        "target_timestamp": NOW - timedelta(hours=1),
        "predicted_consumption_kwh": 100.0,
        "actual_consumption_kwh": 100.0,
        "model_version": "2026-09-16T14-30-00Z",
        "generated_at": NOW - timedelta(hours=2),
        **overrides,
    }
    return ReconciledPrediction(**data)


def test_compute_mae_24h_averages_absolute_error_per_site():
    reconciled = [
        _reconciled(site_id="SITE001", predicted_consumption_kwh=100.0, actual_consumption_kwh=90.0),
        _reconciled(site_id="SITE001", predicted_consumption_kwh=50.0, actual_consumption_kwh=60.0),
        _reconciled(site_id="SITE002", predicted_consumption_kwh=10.0, actual_consumption_kwh=10.0),
    ]

    mae = compute_mae_24h(reconciled, now=NOW)

    assert mae == {"SITE001": 10.0, "SITE002": 0.0}


def test_compute_mae_24h_ignores_predictions_outside_the_window():
    reconciled = [
        _reconciled(target_timestamp=NOW - timedelta(hours=25), predicted_consumption_kwh=100.0, actual_consumption_kwh=0.0),
    ]

    mae = compute_mae_24h(reconciled, now=NOW)

    assert mae == {}


def test_compute_mae_7d_includes_predictions_beyond_24h_but_within_7_days():
    reconciled = [
        _reconciled(
            target_timestamp=NOW - timedelta(days=3),
            predicted_consumption_kwh=100.0,
            actual_consumption_kwh=80.0,
        ),
    ]

    assert compute_mae_24h(reconciled, now=NOW) == {}
    assert compute_mae_7d(reconciled, now=NOW) == {"SITE001": 20.0}


def test_compute_mae_7d_ignores_predictions_older_than_7_days():
    reconciled = [
        _reconciled(
            target_timestamp=NOW - timedelta(days=8),
            predicted_consumption_kwh=100.0,
            actual_consumption_kwh=0.0,
        ),
    ]

    assert compute_mae_7d(reconciled, now=NOW) == {}


def test_latest_model_version_by_site_keeps_the_most_recent_target_timestamp():
    reconciled = [
        _reconciled(target_timestamp=NOW - timedelta(hours=5), model_version="2026-09-15T00-00-00Z"),
        _reconciled(target_timestamp=NOW - timedelta(hours=1), model_version="2026-09-16T14-30-00Z"),
    ]

    versions = latest_model_version_by_site(reconciled, now=NOW)

    assert versions == {"SITE001": "2026-09-16T14-30-00Z"}


def test_compute_drift_score_is_zero_when_distributions_match():
    stats = DistributionStats(mean=100.0, stddev=10.0, count=MIN_SAMPLE_SIZE)

    score = compute_drift_score(recent=stats, training=stats)

    assert score == 0.0


def test_compute_drift_score_reflects_mean_shift():
    training = DistributionStats(mean=100.0, stddev=10.0, count=MIN_SAMPLE_SIZE)
    recent = DistributionStats(mean=130.0, stddev=10.0, count=MIN_SAMPLE_SIZE)

    score = compute_drift_score(recent=recent, training=training)

    assert score == 3.0


def test_compute_drift_score_returns_none_when_sample_too_small():
    training = DistributionStats(mean=100.0, stddev=10.0, count=MIN_SAMPLE_SIZE)
    recent = DistributionStats(mean=130.0, stddev=10.0, count=MIN_SAMPLE_SIZE - 1)

    assert compute_drift_score(recent=recent, training=training) is None


def test_compute_drift_score_returns_none_when_training_stddev_is_zero():
    training = DistributionStats(mean=100.0, stddev=0.0, count=MIN_SAMPLE_SIZE)
    recent = DistributionStats(mean=100.0, stddev=0.0, count=MIN_SAMPLE_SIZE)

    assert compute_drift_score(recent=recent, training=training) is None


def _raw_prediction(**overrides) -> RawPrediction:
    data = {
        "site_id": "SITE001",
        "target_timestamp": NOW,
        "predicted_consumption_kwh": 100.0,
        "model_version": "2026-09-16T14-30-00Z",
        "generated_at": NOW - timedelta(hours=1),
        **overrides,
    }
    return RawPrediction(**data)


def _reading(**overrides) -> ActualReading:
    data = {"site_id": "SITE001", "timestamp": NOW, "consumption_kwh": 95.0, **overrides}
    return ActualReading(**data)


def test_reconcile_predictions_matches_the_closest_reading_within_tolerance():
    # readings_curated.timestamp porte la précision brute de l'API mock,
    # jamais alignée pile sur la minute demandée à /predict (cf. bug
    # constaté en testant contre une vraie stack docker-compose).
    prediction = _raw_prediction(target_timestamp=NOW)
    close_reading = _reading(timestamp=NOW + timedelta(seconds=5), consumption_kwh=95.0)
    far_reading = _reading(timestamp=NOW + timedelta(seconds=250), consumption_kwh=200.0)

    reconciled = reconcile_predictions([prediction], [close_reading, far_reading], tolerance_seconds=300)

    assert reconciled == [
        ReconciledPrediction(
            site_id="SITE001",
            target_timestamp=NOW,
            predicted_consumption_kwh=100.0,
            actual_consumption_kwh=95.0,
            model_version="2026-09-16T14-30-00Z",
            generated_at=NOW - timedelta(hours=1),
        )
    ]


def test_reconcile_predictions_drops_predictions_without_a_close_enough_reading():
    prediction = _raw_prediction(target_timestamp=NOW)
    too_far = _reading(timestamp=NOW + timedelta(seconds=301))

    assert reconcile_predictions([prediction], [too_far], tolerance_seconds=300) == []


def test_reconcile_predictions_ignores_readings_from_other_sites():
    prediction = _raw_prediction(site_id="SITE001", target_timestamp=NOW)
    other_site_reading = _reading(site_id="SITE002", timestamp=NOW)

    assert reconcile_predictions([prediction], [other_site_reading], tolerance_seconds=300) == []


def test_horizon_bucket_label_matches_the_right_range():
    assert horizon_bucket_label(30 * 60) == "0-1h"
    assert horizon_bucket_label(2 * 3600) == "1-3h"
    assert horizon_bucket_label(5 * 24 * 3600) == "3-7j"


def test_horizon_bucket_label_returns_none_out_of_bounds():
    assert horizon_bucket_label(-1) is None
    assert horizon_bucket_label(30 * 24 * 3600) is None


def test_compute_mae_by_horizon_groups_errors_by_site_and_bucket():
    reconciled = [
        _reconciled(
            site_id="SITE001",
            generated_at=NOW - timedelta(minutes=30),
            target_timestamp=NOW,
            predicted_consumption_kwh=100.0,
            actual_consumption_kwh=90.0,
        )
        for _ in range(MIN_HORIZON_SAMPLE_SIZE)
    ] + [
        _reconciled(
            site_id="SITE001",
            generated_at=NOW - timedelta(days=2),
            target_timestamp=NOW,
            predicted_consumption_kwh=100.0,
            actual_consumption_kwh=50.0,
        )
        for _ in range(MIN_HORIZON_SAMPLE_SIZE)
    ]

    result = compute_mae_by_horizon(reconciled)

    assert result == {"SITE001": {"0-1h": 10.0, "1-3j": 50.0}}


def test_compute_mae_by_horizon_omits_buckets_below_min_sample_size():
    reconciled = [
        _reconciled(generated_at=NOW - timedelta(minutes=30), target_timestamp=NOW)
        for _ in range(MIN_HORIZON_SAMPLE_SIZE - 1)
    ]

    assert compute_mae_by_horizon(reconciled) == {}
