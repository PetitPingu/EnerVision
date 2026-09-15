from unittest.mock import Mock, patch

import requests
from domain.entities import Reading, Site
from infrastructure.api_client import ApiMockClient


def _mock_response(json_data, status_code=200):
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} error")
    else:
        mock.raise_for_status.return_value = None
    return mock


def test_get_sites_success():
    client = ApiMockClient(base_url="http://fake:8000")
    sites_payload = [{"site_id": "SITE001", "site_name": "Bureau Paris"}]

    with patch(
        "infrastructure.api_client.requests.get", return_value=_mock_response(sites_payload)
    ) as mock_get:
        sites = client.get_sites()

    assert sites == [Site(site_id="SITE001", site_name="Bureau Paris")]
    mock_get.assert_called_once_with(
        "http://fake:8000/api/v1/sites", params=None, timeout=client.timeout
    )


def test_get_current_reading_success():
    client = ApiMockClient(base_url="http://fake:8000")
    reading_payload = {"site_id": "SITE001", "timestamp": "2024-06-15T14:32:00.123456"}

    with patch(
        "infrastructure.api_client.requests.get", return_value=_mock_response(reading_payload)
    ):
        reading = client.get_current_reading("SITE001")

    assert reading == Reading(site_id="SITE001", timestamp="2024-06-15T14:32:00.123456")


def test_api_unavailable_connection_error_does_not_crash_and_is_logged(caplog):
    client = ApiMockClient(base_url="http://fake:8000")

    with caplog.at_level("ERROR"):
        with patch(
            "infrastructure.api_client.requests.get",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            reading = client.get_current_reading("SITE001")

    assert reading is None
    assert "Échec de l'appel à l'API mock" in caplog.text


def test_api_unavailable_timeout_does_not_crash():
    client = ApiMockClient(base_url="http://fake:8000")

    with patch(
        "infrastructure.api_client.requests.get",
        side_effect=requests.exceptions.Timeout("timeout"),
    ):
        sites = client.get_sites()

    assert sites == []


def test_http_error_returns_default_without_crash():
    client = ApiMockClient(base_url="http://fake:8000")

    with patch(
        "infrastructure.api_client.requests.get", return_value=_mock_response(None, status_code=500)
    ):
        sites = client.get_sites()

    assert sites == []


def test_get_readings_forwards_params_to_api_mock():
    client = ApiMockClient(base_url="http://fake:8000")
    readings_payload = [{"site_id": "SITE002", "timestamp": "2024-01-15T08:00:00"}]

    with patch(
        "infrastructure.api_client.requests.get", return_value=_mock_response(readings_payload)
    ) as mock_get:
        readings = client.get_readings(
            site_id="SITE002", start_time="2024-01-15T08:00:00", limit=48
        )

    assert readings == [Reading(site_id="SITE002", timestamp="2024-01-15T08:00:00")]
    mock_get.assert_called_once_with(
        "http://fake:8000/api/v1/readings",
        params={"limit": 48, "site_id": "SITE002", "start_time": "2024-01-15T08:00:00"},
        timeout=client.timeout,
    )


def test_get_readings_defaults_to_no_filters_and_limit_100():
    client = ApiMockClient(base_url="http://fake:8000")

    with patch(
        "infrastructure.api_client.requests.get", return_value=_mock_response([])
    ) as mock_get:
        client.get_readings()

    mock_get.assert_called_once_with(
        "http://fake:8000/api/v1/readings", params={"limit": 100}, timeout=client.timeout
    )
