from dataclasses import asdict
from unittest.mock import Mock

from domain.entities import Reading, Site
from fastapi.testclient import TestClient
from presentation import api

SITES = [Site(site_id="SITE001", site_name="Bureau Paris")]
READINGS = [Reading(site_id="SITE001", timestamp="2024-06-15T14:32:00.123456", data_quality="good")]


def _client(monkeypatch, sites=None, readings=None):
    mock_api = Mock()
    mock_api.get_sites.return_value = sites if sites is not None else SITES
    mock_api.get_readings.return_value = readings if readings is not None else READINGS
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
