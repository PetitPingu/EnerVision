from unittest.mock import Mock

from domain.entities import AlertEvent, Site
from fastapi.testclient import TestClient
from presentation import api

SITES = [
    Site(site_id="SITE001", site_name="Bureau Paris"),
    Site(site_id="SITE002", site_name="Usine Lyon"),
]


def _client_as(monkeypatch, role, permitted_site_ids=()):
    mock_api = Mock()
    mock_api.get_sites.return_value = SITES
    monkeypatch.setattr(api, "sensor_api", mock_api)

    mock_prediction_api = Mock()
    mock_prediction_api.get_prediction_range.return_value = {"predictions": []}
    monkeypatch.setattr(api, "prediction_api", mock_prediction_api)

    mock_active_alerts_reader = Mock()
    mock_active_alerts_reader.get_active.return_value = [
        AlertEvent(
            event_id="snapshot:SITE001:2026-01-01T00:00:00",
            site_id="SITE001",
            timestamp="2026-01-01T00:00:00",
            data_quality="critical",
        ),
        AlertEvent(
            event_id="snapshot:SITE002:2026-01-01T00:00:00",
            site_id="SITE002",
            timestamp="2026-01-01T00:00:00",
            data_quality="degraded",
        ),
    ]
    monkeypatch.setattr(api, "active_alerts_reader", mock_active_alerts_reader)

    mock_site_access_repo = Mock()
    mock_site_access_repo.get_site_ids.return_value = list(permitted_site_ids)
    monkeypatch.setattr(api, "site_access_repository", mock_site_access_repo)

    monkeypatch.setitem(
        api.app.dependency_overrides,
        api.require_auth,
        lambda: api.CurrentUser(email="user@example.com", role=role, user_id="user-id"),
    )

    return TestClient(api.app), mock_prediction_api


def test_admin_sees_all_sites_without_assignment(monkeypatch):
    client, _ = _client_as(monkeypatch, role="admin", permitted_site_ids=[])

    response = client.get("/api/v1/sites")

    assert response.status_code == 200
    assert {site["site_id"] for site in response.json()} == {"SITE001", "SITE002"}


def test_viewer_only_sees_assigned_sites(monkeypatch):
    client, _ = _client_as(monkeypatch, role="viewer", permitted_site_ids=["SITE001"])

    response = client.get("/api/v1/sites")

    assert response.status_code == 200
    assert [site["site_id"] for site in response.json()] == ["SITE001"]


def test_viewer_with_no_assignments_sees_no_sites(monkeypatch):
    client, _ = _client_as(monkeypatch, role="viewer", permitted_site_ids=[])

    response = client.get("/api/v1/sites")

    assert response.status_code == 200
    assert response.json() == []


def test_viewer_can_query_predictions_for_an_assigned_site(monkeypatch):
    client, mock_prediction_api = _client_as(monkeypatch, role="viewer", permitted_site_ids=["SITE001"])

    response = client.get(
        "/api/v1/predictions/range",
        params={
            "site_id": "SITE001",
            "start_time": "2026-01-01T00:00:00Z",
            "end_time": "2026-01-01T01:00:00Z",
        },
    )

    assert response.status_code == 200
    mock_prediction_api.get_prediction_range.assert_called_once()


def test_viewer_forbidden_from_predictions_for_an_unassigned_site(monkeypatch):
    client, mock_prediction_api = _client_as(monkeypatch, role="viewer", permitted_site_ids=["SITE001"])

    response = client.get(
        "/api/v1/predictions/range",
        params={
            "site_id": "SITE002",
            "start_time": "2026-01-01T00:00:00Z",
            "end_time": "2026-01-01T01:00:00Z",
        },
    )

    assert response.status_code == 403
    mock_prediction_api.get_prediction_range.assert_not_called()


def test_admin_sees_active_alerts_for_every_site(monkeypatch):
    client, _ = _client_as(monkeypatch, role="admin", permitted_site_ids=[])

    response = client.get("/api/v1/alerts/active")

    assert response.status_code == 200
    assert {event["site_id"] for event in response.json()} == {"SITE001", "SITE002"}


def test_viewer_only_sees_active_alerts_for_assigned_sites(monkeypatch):
    client, _ = _client_as(monkeypatch, role="viewer", permitted_site_ids=["SITE001"])

    response = client.get("/api/v1/alerts/active")

    assert response.status_code == 200
    assert [event["site_id"] for event in response.json()] == ["SITE001"]
