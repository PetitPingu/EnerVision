from dataclasses import asdict
from unittest.mock import Mock

from domain.entities import Alert, Reading, Site
from fastapi.testclient import TestClient
from presentation import api

SITES = [Site(site_id="SITE001", site_name="Bureau Paris")]
READINGS = [Reading(site_id="SITE001", timestamp="2024-06-15T14:32:00.123456", data_quality="good")]
ALERTS = [Alert(alert_id="ALR-1", timestamp="2024-06-15T14:32:00.123456", site_id="SITE001")]


_UNSET = object()


def _client(
    monkeypatch,
    sites=None,
    readings=None,
    alerts=None,
    current_reading=_UNSET,
    sensors_status=None,
):
    mock_api = Mock()
    mock_api.get_sites.return_value = sites if sites is not None else SITES
    mock_api.get_readings.return_value = readings if readings is not None else READINGS
    mock_api.get_alerts.return_value = alerts if alerts is not None else ALERTS
    mock_api.get_current_reading.return_value = (
        READINGS[0] if current_reading is _UNSET else current_reading
    )
    mock_api.get_sensors_status.return_value = (
        sensors_status if sensors_status is not None else {"SITE001": {"overall": "ok"}}
    )
    monkeypatch.setattr(api, "sensor_api", mock_api)
    return TestClient(api.app), mock_api


def test_root_lists_endpoints(monkeypatch):
    client, _ = _client(monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "/docs" in response.json()["endpoints"]


def test_health_returns_ok(monkeypatch):
    client, _ = _client(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sites_relays_api_mock_client(monkeypatch):
    client, mock_api = _client(monkeypatch)

    response = client.get("/api/v1/sites")

    assert response.status_code == 200
    assert response.json() == [asdict(site) for site in SITES]
    mock_api.get_sites.assert_called_once()


def test_readings_relays_with_same_params_as_remote_api(monkeypatch):
    client, mock_api = _client(monkeypatch)

    response = client.get(
        "/api/v1/readings",
        params={"site_id": "SITE002", "start_time": "2024-01-15T08:00:00", "limit": 48},
    )

    assert response.status_code == 200
    assert response.json() == [asdict(r) for r in READINGS]
    mock_api.get_readings.assert_called_once_with(
        site_id="SITE002", start_time="2024-01-15T08:00:00", end_time=None, limit=48
    )


def test_readings_defaults_when_no_params(monkeypatch):
    client, mock_api = _client(monkeypatch)

    response = client.get("/api/v1/readings")

    assert response.status_code == 200
    mock_api.get_readings.assert_called_once_with(
        site_id=None, start_time=None, end_time=None, limit=100
    )


def test_current_reading_relays_api_mock_client(monkeypatch):
    client, mock_api = _client(monkeypatch)

    response = client.get("/api/v1/sites/SITE001/current")

    assert response.status_code == 200
    assert response.json() == asdict(READINGS[0])
    mock_api.get_current_reading.assert_called_once_with("SITE001")


def test_current_reading_returns_404_when_unavailable(monkeypatch):
    client, mock_api = _client(monkeypatch, current_reading=None)

    response = client.get("/api/v1/sites/NOPE/current")

    assert response.status_code == 404


def test_alerts_relays_api_mock_client(monkeypatch):
    client, mock_api = _client(monkeypatch)

    response = client.get("/api/v1/alerts", params={"site_id": "SITE001", "severity": "high"})

    assert response.status_code == 200
    assert response.json() == [asdict(a) for a in ALERTS]
    mock_api.get_alerts.assert_called_once_with(site_id="SITE001", severity="high")


def test_sensors_status_relays_api_mock_client(monkeypatch):
    client, mock_api = _client(monkeypatch)

    response = client.get("/api/v1/sensors/status")

    assert response.status_code == 200
    assert response.json() == {"SITE001": {"overall": "ok"}}
    mock_api.get_sensors_status.assert_called_once()
