from dataclasses import asdict
from unittest.mock import AsyncMock, Mock

import pytest
from domain.entities import Alert, AlertEvent, Reading, Site
from fastapi.testclient import TestClient
from presentation import api
from presentation.api import _sse_alert_events
from infrastructure.prediction_client import PredictionModelNotLoadedError

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
    recommendations=_UNSET,
    mock_prediction_api=None,
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

    mock_recommendation_api = Mock()
    mock_recommendation_api.get_recommendations.return_value = (
        [] if recommendations is _UNSET else recommendations
    )
    monkeypatch.setattr(api, "recommendation_api", mock_recommendation_api)

    if mock_prediction_api is not None:
        monkeypatch.setattr(api, "prediction_api", mock_prediction_api)

    # Ces tests portent sur la logique métier des routes, pas sur l'auth ni
    # le filtrage par site (voir tests/test_auth.py et test_admin.py) : on
    # neutralise require_auth avec un admin, qui voit tout sans filtrage
    # (voir _permitted_site_ids).
    monkeypatch.setitem(
        api.app.dependency_overrides,
        api.require_auth,
        lambda: api.CurrentUser(email="test@example.com", role="admin", user_id=None),
    )

    return TestClient(api.app), mock_api, mock_recommendation_api


def test_root_lists_endpoints(monkeypatch):
    client, _, _ = _client(monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "/docs" in response.json()["endpoints"]


def test_health_returns_ok(monkeypatch):
    client, _, _ = _client(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sites_relays_api_mock_client(monkeypatch):
    client, mock_api, _ = _client(monkeypatch)

    response = client.get("/api/v1/sites")

    assert response.status_code == 200
    assert response.json() == [asdict(site) for site in SITES]
    mock_api.get_sites.assert_called_once()


def test_readings_relays_with_same_params_as_remote_api(monkeypatch):
    client, mock_api, _ = _client(monkeypatch)

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
    client, mock_api, _ = _client(monkeypatch)

    response = client.get("/api/v1/readings")

    assert response.status_code == 200
    mock_api.get_readings.assert_called_once_with(
        site_id=None, start_time=None, end_time=None, limit=100
    )


def test_current_reading_relays_api_mock_client(monkeypatch):
    client, mock_api, _ = _client(monkeypatch)

    response = client.get("/api/v1/sites/SITE001/current")

    assert response.status_code == 200
    assert response.json() == asdict(READINGS[0])
    mock_api.get_current_reading.assert_called_once_with("SITE001")


def test_current_reading_returns_404_when_unavailable(monkeypatch):
    client, mock_api, _ = _client(monkeypatch, current_reading=None)

    response = client.get("/api/v1/sites/NOPE/current")

    assert response.status_code == 404


def test_alerts_relays_api_mock_client(monkeypatch):
    client, mock_api, _ = _client(monkeypatch)

    response = client.get("/api/v1/alerts", params={"site_id": "SITE001", "severity": "high"})

    assert response.status_code == 200
    assert response.json() == [asdict(a) for a in ALERTS]
    mock_api.get_alerts.assert_called_once_with(site_id="SITE001", severity="high")


def test_active_alerts_relays_active_alerts_reader(monkeypatch):
    event = AlertEvent(
        event_id="snapshot:SITE002:2026-09-18T08:20:17",
        site_id="SITE002",
        timestamp="2026-09-18T08:20:17",
        data_quality="critical",
        null_reasons=["network_loss"],
    )
    mock_reader = Mock()
    mock_reader.get_active.return_value = [event]
    monkeypatch.setattr(api, "active_alerts_reader", mock_reader)
    client, _, _ = _client(monkeypatch)

    response = client.get("/api/v1/alerts/active")

    assert response.status_code == 200
    assert response.json() == [
        {
            "event_id": "snapshot:SITE002:2026-09-18T08:20:17",
            "site_id": "SITE002",
            "timestamp": "2026-09-18T08:20:17",
            "data_quality": "critical",
            "null_reasons": ["network_loss"],
            "kind": "alert",
        }
    ]
    mock_reader.get_active.assert_called_once()


def test_active_alerts_serializes_partial_as_minor_alert_kind(monkeypatch):
    event = AlertEvent(
        event_id="snapshot:SITE005:2026-09-18T08:59:17",
        site_id="SITE005",
        timestamp="2026-09-18T08:59:17",
        data_quality="partial",
        null_reasons=["temperature_sensor_failure"],
    )
    mock_reader = Mock()
    mock_reader.get_active.return_value = [event]
    monkeypatch.setattr(api, "active_alerts_reader", mock_reader)
    client, _, _ = _client(monkeypatch)

    response = client.get("/api/v1/alerts/active")

    assert response.json()[0]["kind"] == "minor_alert"


def test_sensors_status_relays_api_mock_client(monkeypatch):
    client, mock_api, _ = _client(monkeypatch)

    response = client.get("/api/v1/sensors/status")

    assert response.status_code == 200
    assert response.json() == {"SITE001": {"overall": "ok"}}
    mock_api.get_sensors_status.assert_called_once()


def test_recommendations_relays_recommendation_api_client(monkeypatch):
    payload = [{"site_id": "SITE001", "action": "load_shifting", "justification": "..."}]
    client, _, mock_recommendation_api = _client(monkeypatch, recommendations=payload)

    response = client.get("/api/v1/recommendations", params={"site_id": "SITE001"})

    assert response.status_code == 200
    assert response.json() == payload
    mock_recommendation_api.get_recommendations.assert_called_once_with(site_id="SITE001")


def test_recommendations_returns_502_when_service_unavailable(monkeypatch):
    client, _, mock_recommendation_api = _client(monkeypatch)
    mock_recommendation_api.get_recommendations.return_value = None

    response = client.get("/api/v1/recommendations", params={"site_id": "SITE001"})

    assert response.status_code == 502


def test_recommendations_requires_site_id(monkeypatch):
    client, _, _ = _client(monkeypatch)

    response = client.get("/api/v1/recommendations")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sse_alert_events_yields_formatted_events_then_stops():
    event = AlertEvent(
        event_id="1-0", site_id="SITE001", timestamp="2026-09-15T10:00:00", data_quality="critical"
    )
    stream = AsyncMock()
    stream.read_new.side_effect = [[event], []]
    request = Mock()
    request.is_disconnected = AsyncMock(side_effect=[False, False, True])

    generator = _sse_alert_events(request, stream)

    first = await anext(generator)
    assert first.startswith("event: alert\ndata: ")
    assert '"site_id": "SITE001"' in first

    second = await anext(generator)
    assert second == ": heartbeat\n\n"

    with pytest.raises(StopAsyncIteration):
        await anext(generator)


def test_alerts_stream_route_returns_sse_content_type(monkeypatch):
    mock_stream = AsyncMock()
    monkeypatch.setattr(api, "alert_stream", mock_stream)
    monkeypatch.setattr(api.Request, "is_disconnected", AsyncMock(return_value=True))
    # Le lifespan préchauffe le cache de sites au démarrage (cf.
    # presentation/api.py) : on mocke sensor_api pour ne pas appeler la
    # vraie API mock pendant ce test, qui utilise le vrai lifespan (context
    # manager TestClient) pour le SSE.
    monkeypatch.setattr(api, "sensor_api", Mock(get_sites=Mock(return_value=[])))

    with TestClient(api.app) as client:
        response = client.get("/api/v1/alerts/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_predictions_sensors_relays_prediction_api_client(monkeypatch):
    payload = {
        "site_id": "SITE001",
        "target_timestamp": "2026-09-17T14:30:00Z",
        "sensors": {"voltage_v": "on", "humidity_percent": "off"},
        "model_version": "2026-09-16T14-30-00Z",
    }
    mock_prediction_api = Mock()
    mock_prediction_api.get_sensor_state.return_value = payload
    client, _, _ = _client(monkeypatch, mock_prediction_api=mock_prediction_api)

    response = client.get(
        "/api/v1/predictions/sensors",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 200
    assert response.json() == payload
    mock_prediction_api.get_sensor_state.assert_called_once_with(
        site_id="SITE001", timestamp="2026-09-17T14:30:00Z"
    )


def test_predictions_sensors_returns_502_when_service_unavailable(monkeypatch):
    mock_prediction_api = Mock()
    mock_prediction_api.get_sensor_state.return_value = None
    client, _, _ = _client(monkeypatch, mock_prediction_api=mock_prediction_api)

    response = client.get(
        "/api/v1/predictions/sensors",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 502


def test_predictions_sensors_returns_503_when_model_not_loaded(monkeypatch):
    mock_prediction_api = Mock()
    mock_prediction_api.get_sensor_state.side_effect = PredictionModelNotLoadedError()
    client, _, _ = _client(monkeypatch, mock_prediction_api=mock_prediction_api)

    response = client.get(
        "/api/v1/predictions/sensors",
        params={"site_id": "SITE001", "timestamp": "2026-09-17T14:30:00Z"},
    )

    assert response.status_code == 503


def test_predictions_sensors_requires_timestamp(monkeypatch):
    client, _, _ = _client(monkeypatch)

    response = client.get("/api/v1/predictions/sensors", params={"site_id": "SITE001"})

    assert response.status_code == 422
