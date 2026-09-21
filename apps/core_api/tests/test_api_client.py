from unittest.mock import Mock, patch

from domain.entities import Reading, Site
from infrastructure.api_client import ApiMockClient
from infrastructure.config import Config
from mockapi_client import EnergyReading, MockApiConnectionError, MockApiHTTPError, MockApiTimeoutError
from mockapi_client import Alert as MockAlert
from mockapi_client import Site as MockSite


def _make_client(mock_inner: Mock) -> ApiMockClient:
    with patch("infrastructure.api_client.MockApiClient", return_value=mock_inner):
        return ApiMockClient(base_url="http://fake:8000")


def _mock_site(site_id="SITE001", **overrides) -> MockSite:
    data = {
        "site_id": site_id,
        "site_type": "office",
        "site_name": "Bureau Paris",
        "location": "Paris, France",
        "capacity_kw": 200.0,
        "status": "active",
        **overrides,
    }
    return MockSite(**data)


def _mock_reading(site_id="SITE001", **overrides) -> EnergyReading:
    data = {
        "timestamp": "2024-06-15T14:32:00.123456",
        "site_id": site_id,
        "site_type": "office",
        "consumption_kw": 100.0,
        "consumption_kwh": 100.0,
        "voltage_v": 400.0,
        "current_a": 144.0,
        "power_factor": 0.95,
        "temperature_celsius": 20.0,
        "humidity_percent": 40.0,
        "null_reasons": [],
        "data_quality": "good",
        **overrides,
    }
    return EnergyReading(**data)


def test_get_sites_success():
    mock_inner = Mock()
    mock_inner.get_sites.return_value = [_mock_site()]
    client = _make_client(mock_inner)

    sites = client.get_sites()

    assert sites == [
        Site(
            site_id="SITE001",
            site_name="Bureau Paris",
            site_type="office",
            location="Paris, France",
            capacity_kw=200.0,
            status="active",
        )
    ]


def test_get_sites_is_cached_within_ttl():
    mock_inner = Mock()
    mock_inner.get_sites.return_value = [_mock_site()]
    client = _make_client(mock_inner)

    client.get_sites()
    client.get_sites()

    mock_inner.get_sites.assert_called_once()


def test_get_sites_refetches_after_ttl_expires():
    mock_inner = Mock()
    mock_inner.get_sites.return_value = [_mock_site()]
    client = _make_client(mock_inner)

    with patch("infrastructure.api_client.time.monotonic", side_effect=[0.0, 1000.0]):
        client.get_sites()
        client.get_sites()

    assert mock_inner.get_sites.call_count == 2


def test_get_sites_falls_back_to_stale_cache_on_error():
    mock_inner = Mock()
    mock_inner.get_sites.return_value = [_mock_site()]
    client = _make_client(mock_inner)

    with patch("infrastructure.api_client.time.monotonic", side_effect=[0.0, 1000.0]):
        first = client.get_sites()

        mock_inner.get_sites.side_effect = MockApiHTTPError(401, "rate limited")
        second = client.get_sites()

    assert second == first
    assert second != []


def test_get_current_reading_success():
    mock_inner = Mock()
    mock_inner.get_current.return_value = _mock_reading()
    client = _make_client(mock_inner)

    reading = client.get_current_reading("SITE001")

    assert reading == Reading(
        site_id="SITE001",
        timestamp="2024-06-15T14:32:00.123456",
        site_type="office",
        consumption_kw=100.0,
        consumption_kwh=100.0,
        voltage_v=400.0,
        current_a=144.0,
        power_factor=0.95,
        temperature_celsius=20.0,
        humidity_percent=40.0,
        null_reasons=[],
        data_quality="good",
    )
    mock_inner.get_current.assert_called_once_with("SITE001")


def test_api_unavailable_connection_error_does_not_crash_and_is_logged(caplog):
    mock_inner = Mock()
    mock_inner.get_current.side_effect = MockApiConnectionError("boom")
    client = _make_client(mock_inner)

    with caplog.at_level("ERROR"):
        reading = client.get_current_reading("SITE001")

    assert reading is None
    assert "Échec de l'appel à l'API mock" in caplog.text


def test_api_unavailable_timeout_does_not_crash():
    mock_inner = Mock()
    mock_inner.get_sites.side_effect = MockApiTimeoutError("timeout")
    client = _make_client(mock_inner)

    sites = client.get_sites()

    assert sites == []


def test_http_error_returns_default_without_crash():
    mock_inner = Mock()
    mock_inner.get_sites.side_effect = MockApiHTTPError(500, "server error")
    client = _make_client(mock_inner)

    sites = client.get_sites()

    assert sites == []


def test_get_readings_forwards_params_to_api_mock():
    mock_inner = Mock()
    mock_inner.get_readings.return_value = [_mock_reading(site_id="SITE002")]
    client = _make_client(mock_inner)

    readings = client.get_readings(site_id="SITE002", start_time="2024-01-15T08:00:00", limit=48)

    assert [r.site_id for r in readings] == ["SITE002"]
    mock_inner.get_readings.assert_called_once_with(
        site_id="SITE002", start="2024-01-15T08:00:00", end=None, limit=48
    )


def test_get_readings_defaults_to_no_filters_and_limit_100():
    mock_inner = Mock()
    mock_inner.get_readings.return_value = []
    client = _make_client(mock_inner)

    client.get_readings()

    mock_inner.get_readings.assert_called_once_with(site_id=None, start=None, end=None, limit=100)


def _mock_alert(**overrides) -> MockAlert:
    data = {
        "alert_id": "ALR-SITE001-1",
        "timestamp": "2026-09-15T09:25:13.941004",
        "site_id": "SITE001",
        "severity": "medium",
        "type": "threshold",
        "message": "Seuil dépassé",
        "value": 159.6,
        "threshold": 135.0,
        **overrides,
    }
    return MockAlert(**data)


def test_get_alerts_success():
    mock_inner = Mock()
    mock_inner.get_alerts.return_value = [_mock_alert()]
    client = _make_client(mock_inner)

    alerts = client.get_alerts(site_id="SITE001", severity="medium")

    assert len(alerts) == 1
    assert alerts[0].alert_id == "ALR-SITE001-1"
    assert alerts[0].value == 159.6
    mock_inner.get_alerts.assert_called_once_with(site_id="SITE001", severity="medium")


def test_get_alerts_returns_empty_list_on_error():
    mock_inner = Mock()
    mock_inner.get_alerts.side_effect = MockApiHTTPError(500, "server error")
    client = _make_client(mock_inner)

    alerts = client.get_alerts()

    assert alerts == []


def test_get_sensors_status_success():
    mock_inner = Mock()
    status_payload = {"SITE001": {"overall": "ok"}}
    mock_inner.get_sensors_status.return_value = status_payload
    client = _make_client(mock_inner)

    status = client.get_sensors_status()

    assert status == status_payload


def test_get_sensors_status_returns_empty_dict_on_error():
    mock_inner = Mock()
    mock_inner.get_sensors_status.side_effect = MockApiConnectionError("boom")
    client = _make_client(mock_inner)

    status = client.get_sensors_status()

    assert status == {}
