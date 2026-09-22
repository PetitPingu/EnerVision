from unittest.mock import Mock

from application.etl_job import EtlJob
from domain.data_quality_transition import DataQualityTransitionDetector
from domain.imputation import ConsumptionKwhImputer
from mockapi_client import EnergyReading, MockApiTimeoutError


def _reading(**overrides) -> EnergyReading:
    data = {
        "timestamp": "2026-09-15T10:00:13.879434",
        "site_id": "SITE001",
        "site_type": "office",
        "consumption_kw": 154.4,
        "consumption_kwh": 154.4,
        "voltage_v": 404.4,
        "current_a": 232.04,
        "power_factor": 0.946,
        "temperature_celsius": 8.5,
        "humidity_percent": 38.0,
        "null_reasons": [],
        "data_quality": "good",
        **overrides,
    }
    reading = EnergyReading(**data)
    reading.raw_payload = b'{"fake": "payload"}'
    return reading


def _critical_reading(**overrides) -> EnergyReading:
    return _reading(
        consumption_kw=None,
        consumption_kwh=None,
        voltage_v=None,
        current_a=None,
        power_factor=None,
        temperature_celsius=None,
        humidity_percent=None,
        null_reasons=["network_outage"],
        data_quality="critical",
        **overrides,
    )


def _job(**overrides):
    defaults = dict(
        api_client=Mock(), raw_writer=Mock(), curated_writer=Mock(), alert_publisher=Mock()
    )
    defaults.update(overrides)
    job = EtlJob(**defaults)
    job.raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"
    return job


def test_run_calls_get_readings_with_limit_7():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading()]
    job = _job(api_client=api_client)

    job.run()

    _, kwargs = api_client.get_readings.call_args
    assert kwargs["limit"] == 7


def test_process_writes_raw_payload_unmodified():
    reading = _reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()

    raw_writer.write.assert_called_once_with(
        site_id="SITE001", timestamp=reading.timestamp, raw_payload=reading.raw_payload
    )


def test_critical_reading_is_written_like_any_other():
    reading = _critical_reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.return_value = "SITE001/2026/09/15/17/30.json"

    job = _job(api_client=api_client, raw_writer=raw_writer)
    job.run()

    raw_writer.write.assert_called_once()


def test_raw_write_failure_excludes_the_reading_but_does_not_crash():
    reading = _reading()
    api_client = Mock()
    api_client.get_readings.return_value = [reading]
    raw_writer = Mock()
    raw_writer.write.side_effect = RuntimeError("minio down")
    curated_writer = Mock()

    job = _job(api_client=api_client, raw_writer=raw_writer, curated_writer=curated_writer)
    job.run()  # ne doit pas lever

    curated_writer.upsert_many.assert_not_called()


def test_api_error_does_not_crash_and_writes_nothing():
    api_client = Mock()
    api_client.get_readings.side_effect = MockApiTimeoutError("timeout")
    raw_writer = Mock()
    curated_writer = Mock()

    job = _job(api_client=api_client, raw_writer=raw_writer, curated_writer=curated_writer)
    job.run()  # ne doit pas lever

    raw_writer.write.assert_not_called()
    curated_writer.upsert_many.assert_not_called()


def test_run_processes_all_readings_returned():
    readings = [_reading(site_id=f"SITE00{i}") for i in range(1, 8)]
    api_client = Mock()
    api_client.get_readings.return_value = readings
    raw_writer = Mock()
    raw_writer.write.return_value = "x.json"
    curated_writer = Mock()

    job = _job(api_client=api_client, raw_writer=raw_writer, curated_writer=curated_writer)
    job.run()

    args, _ = curated_writer.upsert_many.call_args
    assert len(args[0]) == 7


def test_curated_write_failure_does_not_crash():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading()]
    curated_writer = Mock()
    curated_writer.upsert_many.side_effect = RuntimeError("postgres down")

    job = _job(api_client=api_client, curated_writer=curated_writer)
    job.run()  # ne doit pas lever


def test_missing_consumption_kwh_is_forward_filled_from_the_previous_cycle():
    api_client = Mock()
    curated_writer = Mock()
    imputer = ConsumptionKwhImputer()
    job = _job(api_client=api_client, curated_writer=curated_writer, imputer=imputer)

    api_client.get_readings.return_value = [_reading(consumption_kwh=42.0)]
    job.run()

    api_client.get_readings.return_value = [
        _reading(timestamp="2026-09-15T10:01:00", consumption_kwh=None, data_quality="partial")
    ]
    job.run()

    args, _ = curated_writer.upsert_many.call_args
    curated_row = args[0][0]
    assert curated_row["consumption_kwh"] == 42.0
    assert curated_row["imputation_methods"] == "forward_fill"


def test_missing_consumption_kwh_with_no_prior_reading_stays_none_with_no_history():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading(consumption_kwh=None, data_quality="partial")]
    curated_writer = Mock()

    job = _job(api_client=api_client, curated_writer=curated_writer)
    job.run()

    args, _ = curated_writer.upsert_many.call_args
    curated_row = args[0][0]
    assert curated_row["consumption_kwh"] is None
    assert curated_row["imputation_methods"] == "no_history"


def test_known_consumption_kwh_has_no_imputation_method():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading(consumption_kwh=42.0)]
    curated_writer = Mock()

    job = _job(api_client=api_client, curated_writer=curated_writer)
    job.run()

    args, _ = curated_writer.upsert_many.call_args
    curated_row = args[0][0]
    assert curated_row["imputation_methods"] is None


def test_transition_to_critical_publishes_alert_event():
    api_client = Mock()
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )

    api_client.get_readings.return_value = [_reading(data_quality="good")]
    job.run()
    alert_publisher.publish.assert_not_called()

    api_client.get_readings.return_value = [_critical_reading()]
    job.run()

    alert_publisher.publish.assert_called_once_with(
        site_id="SITE001",
        timestamp="2026-09-15T10:00:13.879434",
        data_quality="critical",
        null_reasons=["network_outage"],
    )


def test_transition_to_degraded_publishes_alert_event():
    api_client = Mock()
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )

    api_client.get_readings.return_value = [_reading(data_quality="good")]
    job.run()

    api_client.get_readings.return_value = [_reading(data_quality="degraded")]
    job.run()

    alert_publisher.publish.assert_called_once()
    assert alert_publisher.publish.call_args.kwargs["data_quality"] == "degraded"


def test_transition_from_critical_to_good_publishes_recovery_event():
    api_client = Mock()
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )

    api_client.get_readings.return_value = [_reading(data_quality="good")]
    job.run()
    api_client.get_readings.return_value = [_critical_reading()]
    job.run()
    alert_publisher.reset_mock()

    api_client.get_readings.return_value = [_reading(data_quality="good")]
    job.run()

    alert_publisher.publish.assert_called_once()
    assert alert_publisher.publish.call_args.kwargs["data_quality"] == "good"


def test_repeated_critical_readings_publish_alert_only_once():
    api_client = Mock()
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )

    api_client.get_readings.return_value = [_reading(data_quality="good")]
    job.run()

    api_client.get_readings.return_value = [_critical_reading()]
    job.run()
    job.run()
    job.run()

    alert_publisher.publish.assert_called_once()


def test_transition_to_partial_publishes_minor_alert_event():
    api_client = Mock()
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )

    api_client.get_readings.return_value = [_reading(data_quality="good")]
    job.run()

    api_client.get_readings.return_value = [_reading(data_quality="partial")]
    job.run()

    alert_publisher.publish.assert_called_once()
    assert alert_publisher.publish.call_args.kwargs["data_quality"] == "partial"


def test_repeated_partial_readings_publish_minor_alert_only_once():
    api_client = Mock()
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )

    api_client.get_readings.return_value = [_reading(data_quality="good")]
    job.run()

    api_client.get_readings.return_value = [_reading(data_quality="partial")]
    job.run()
    job.run()
    job.run()

    alert_publisher.publish.assert_called_once()


def test_redis_publish_failure_does_not_crash_cycle():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading(data_quality="good")]
    curated_writer = Mock()
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        curated_writer=curated_writer,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )
    job.run()

    alert_publisher.publish.side_effect = RuntimeError("redis down")
    api_client.get_readings.return_value = [_critical_reading()]
    job.run()  # ne doit pas lever

    curated_writer.upsert_many.assert_called()


def test_failed_publish_is_retried_on_the_next_cycle_once_redis_is_back():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading(data_quality="good")]
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )
    job.run()

    alert_publisher.publish.side_effect = RuntimeError("redis down")
    api_client.get_readings.return_value = [_critical_reading()]
    job.run()  # publication échoue : la transition n'est pas commitée
    alert_publisher.publish.assert_called_once()

    alert_publisher.publish.side_effect = None  # Redis est de retour
    job.run()  # même lecture critical : doit retenter la même transition

    assert alert_publisher.publish.call_count == 2
    assert alert_publisher.publish.call_args.kwargs["data_quality"] == "critical"


def test_alert_publish_happens_even_when_raw_write_fails():
    api_client = Mock()
    api_client.get_readings.return_value = [_reading(data_quality="good")]
    alert_publisher = Mock()
    transition_detector = DataQualityTransitionDetector()
    job = _job(
        api_client=api_client,
        alert_publisher=alert_publisher,
        transition_detector=transition_detector,
    )
    job.run()

    job.raw_writer.write.side_effect = RuntimeError("minio down")
    api_client.get_readings.return_value = [_critical_reading()]
    job.run()

    alert_publisher.publish.assert_called_once()
