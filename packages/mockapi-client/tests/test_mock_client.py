import json
import pathlib
import re
from unittest.mock import Mock, patch

import pytest
import requests
from mockapi_client import (
    Alert,
    MockApiClient,
    MockApiConnectionError,
    MockApiNotFoundError,
    MockApiTimeoutError,
    MockApiValidationError,
)

BASE_URL = "http://fake:8000"

READING_GOOD = {
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
}

READING_PARTIAL = {
    **READING_GOOD,
    "humidity_percent": None,
    "null_reasons": ["humidity_sensor_failure"],
    "data_quality": "partial",
}

READING_DEGRADED = {
    **READING_GOOD,
    "humidity_percent": None,
    "temperature_celsius": None,
    "voltage_v": None,
    "null_reasons": [
        "humidity_sensor_failure",
        "temperature_sensor_failure",
        "electrical_sensor_failure",
    ],
    "data_quality": "degraded",
}

READING_CRITICAL = {
    "timestamp": "2026-09-15T10:00:13.879434",
    "site_id": "SITE002",
    "site_type": "factory",
    "consumption_kw": None,
    "consumption_kwh": None,
    "voltage_v": None,
    "current_a": None,
    "power_factor": None,
    "temperature_celsius": None,
    "humidity_percent": None,
    "null_reasons": ["network_outage"],
    "data_quality": "critical",
}


def _mock_response(json_data, status_code=200):
    body = json.dumps(json_data, ensure_ascii=False).encode("utf-8")
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.content = body
    mock.text = body.decode("utf-8")
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} error")
    else:
        mock.raise_for_status.return_value = None
    return mock


def _client(**kwargs):
    kwargs.setdefault("backoff_base", 0.001)
    return MockApiClient(base_url=BASE_URL, **kwargs)


@pytest.mark.parametrize(
    "payload",
    [READING_GOOD, READING_PARTIAL, READING_DEGRADED, READING_CRITICAL],
    ids=["good", "partial", "degraded", "critical"],
)
def test_get_current_parses_all_data_quality_levels(payload):
    client = _client()
    with patch("mockapi_client.mock_client.requests.get", return_value=_mock_response(payload)):
        reading = client.get_current(payload["site_id"])

    assert reading.data_quality == payload["data_quality"]
    assert reading.null_reasons == payload["null_reasons"]


def test_response_with_nulls_parses_without_exception_and_keeps_null_reasons():
    client = _client()
    with patch(
        "mockapi_client.mock_client.requests.get", return_value=_mock_response(READING_PARTIAL)
    ):
        reading = client.get_current("SITE001")

    assert reading.humidity_percent is None
    assert reading.null_reasons == ["humidity_sensor_failure"]


def test_critical_reading_is_returned_not_discarded_nor_raised():
    client = _client()
    with patch(
        "mockapi_client.mock_client.requests.get", return_value=_mock_response(READING_CRITICAL)
    ):
        reading = client.get_current("SITE002")

    assert reading.data_quality == "critical"
    assert reading.consumption_kw is None
    assert reading.voltage_v is None


def test_round_trip_serialization_matches_original_payload_exactly():
    client = _client()
    with patch(
        "mockapi_client.mock_client.requests.get", return_value=_mock_response(READING_PARTIAL)
    ):
        reading = client.get_current("SITE001")

    assert reading.model_dump(mode="json") == READING_PARTIAL


def test_raw_payload_is_byte_identical_to_response_body():
    client = _client()
    response = _mock_response(READING_GOOD)
    with patch("mockapi_client.mock_client.requests.get", return_value=response):
        reading = client.get_current("SITE001")

    assert reading.raw_payload == response.content
    assert json.loads(reading.raw_payload) == READING_GOOD


def test_timeout_raises_dedicated_exception_not_generic_crash():
    client = _client(max_retries=1)
    with patch(
        "mockapi_client.mock_client.requests.get",
        side_effect=requests.exceptions.Timeout("boom"),
    ) as mock_get:
        with pytest.raises(MockApiTimeoutError):
            client.get_current("SITE001")

    assert mock_get.call_count == 2  # 1 tentative + 1 retry


def test_connection_error_retries_then_raises_dedicated_exception():
    client = _client(max_retries=2)
    with patch(
        "mockapi_client.mock_client.requests.get",
        side_effect=requests.exceptions.ConnectionError("boom"),
    ) as mock_get:
        with pytest.raises(MockApiConnectionError):
            client.get_sites()

    assert mock_get.call_count == 3  # 1 tentative + 2 retries


def test_5xx_is_retried_then_succeeds():
    client = _client(max_retries=3)
    site_payload = [
        {
            "site_id": "SITE001",
            "site_type": "office",
            "site_name": "Bureau Paris La Défense",
            "location": "Paris, France",
            "capacity_kw": 200.0,
            "status": "active",
        }
    ]
    responses = [
        _mock_response(None, status_code=503),
        _mock_response(None, status_code=503),
        _mock_response(site_payload),
    ]
    with patch("mockapi_client.mock_client.requests.get", side_effect=responses) as mock_get:
        sites = client.get_sites()

    assert len(sites) == 1
    assert sites[0].site_id == "SITE001"
    assert mock_get.call_count == 3


def test_404_raises_not_found_without_retry():
    client = _client(max_retries=3)
    with patch(
        "mockapi_client.mock_client.requests.get",
        return_value=_mock_response({"detail": "Site NOPE non trouvé"}, status_code=404),
    ) as mock_get:
        with pytest.raises(MockApiNotFoundError):
            client.get_current("NOPE")

    assert mock_get.call_count == 1


def test_422_raises_validation_error_without_retry():
    client = _client(max_retries=3)
    with patch(
        "mockapi_client.mock_client.requests.get",
        return_value=_mock_response({"detail": [{"msg": "invalid"}]}, status_code=422),
    ) as mock_get:
        with pytest.raises(MockApiValidationError):
            client.get_readings(limit=99999)

    assert mock_get.call_count == 1


def test_get_alerts_parses_payload():
    alert_payload = [
        {
            "alert_id": "ALR-SITE001-1",
            "timestamp": "2026-09-15T09:25:13.941004",
            "site_id": "SITE001",
            "severity": "medium",
            "type": "threshold",
            "message": "Seuil dépassé",
            "value": 159.6,
            "threshold": 135.0,
        }
    ]
    client = _client()
    with patch(
        "mockapi_client.mock_client.requests.get", return_value=_mock_response(alert_payload)
    ):
        alerts = client.get_alerts(site_id="SITE001")

    assert len(alerts) == 1
    assert isinstance(alerts[0], Alert)
    assert alerts[0].alert_id == "ALR-SITE001-1"
    assert alerts[0].value == 159.6


def test_get_sensors_status_returns_raw_dict():
    status_payload = {"SITE001": {"site_name": "Bureau", "sensors": {}, "overall": "ok"}}
    client = _client()
    with patch(
        "mockapi_client.mock_client.requests.get", return_value=_mock_response(status_payload)
    ):
        status = client.get_sensors_status()

    assert status == status_payload


def test_no_requests_get_outside_mock_client_module():
    """Aucun appel requests.get en dehors de ce module dans tout le repo."""
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    allowed_file = (
        pathlib.Path(__file__).resolve().parents[1] / "src" / "mockapi_client" / "mock_client.py"
    )
    pattern = re.compile(r"\brequests\.get\s*\(")
    ignored_dirs = {".git", "__pycache__", "node_modules", "venv", ".venv"}

    offenders = []
    for path in repo_root.rglob("*.py"):
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.resolve() == allowed_file:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            offenders.append(str(path.relative_to(repo_root)))

    assert offenders == [], f"requests.get trouvé en dehors de mock_client.py : {offenders}"
