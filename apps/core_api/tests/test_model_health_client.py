from unittest.mock import Mock

import requests
from infrastructure.model_health_client import ModelHealthClient


def _client(monkeypatch, response=None, raises=None):
    mock_get = Mock()
    if raises is not None:
        mock_get.side_effect = raises
    else:
        mock_get.return_value = response
    monkeypatch.setattr(requests, "get", mock_get)
    return ModelHealthClient(base_url="http://fake:9090"), mock_get


def _response(json_data, status_ok=True):
    response = Mock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("boom")
    return response


def _prometheus_payload(value: str, metric_name: str = "ml_feature_drift_score"):
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"__name__": metric_name, "site": "SITE001"},
                    "value": [1758470400, value],
                }
            ],
        },
    }


def test_get_drift_score_parses_prometheus_response(monkeypatch):
    client, mock_get = _client(
        monkeypatch, response=_response(_prometheus_payload("3.42"))
    )

    result = client.get_drift_score("SITE001")

    assert result == 3.42
    mock_get.assert_called_once_with(
        "http://fake:9090/api/v1/query",
        params={"query": 'ml_feature_drift_score{site="SITE001"}'},
        timeout=5.0,
    )


def test_get_drift_score_returns_none_when_metric_is_absent(monkeypatch):
    payload = {"status": "success", "data": {"resultType": "vector", "result": []}}
    client, _ = _client(monkeypatch, response=_response(payload))

    assert client.get_drift_score("SITE001") is None


def test_get_drift_score_returns_none_on_http_error(monkeypatch, caplog):
    client, _ = _client(monkeypatch, response=_response({}, status_ok=False))

    with caplog.at_level("ERROR"):
        result = client.get_drift_score("SITE001")

    assert result is None
    assert "Échec de l'appel à Prometheus" in caplog.text


def test_get_drift_score_returns_none_when_prometheus_unreachable(monkeypatch):
    client, _ = _client(monkeypatch, raises=requests.ConnectionError("refused"))

    assert client.get_drift_score("SITE001") is None


def test_get_mae_24h_parses_prometheus_response(monkeypatch):
    client, mock_get = _client(
        monkeypatch,
        response=_response(_prometheus_payload("12.5", metric_name="ml_prediction_mae_24h")),
    )

    result = client.get_mae_24h("SITE001")

    assert result == 12.5
    mock_get.assert_called_once_with(
        "http://fake:9090/api/v1/query",
        params={"query": 'ml_prediction_mae_24h{site="SITE001"}'},
        timeout=5.0,
    )


def test_get_mae_24h_returns_none_when_metric_is_absent(monkeypatch):
    payload = {"status": "success", "data": {"resultType": "vector", "result": []}}
    client, _ = _client(monkeypatch, response=_response(payload))

    assert client.get_mae_24h("SITE001") is None


def test_get_mae_7d_parses_prometheus_response(monkeypatch):
    client, mock_get = _client(
        monkeypatch,
        response=_response(_prometheus_payload("30.0", metric_name="ml_prediction_mae_7d")),
    )

    result = client.get_mae_7d("SITE001")

    assert result == 30.0
    mock_get.assert_called_once_with(
        "http://fake:9090/api/v1/query",
        params={"query": 'ml_prediction_mae_7d{site="SITE001"}'},
        timeout=5.0,
    )


def test_get_mae_7d_returns_none_when_metric_is_absent(monkeypatch):
    payload = {"status": "success", "data": {"resultType": "vector", "result": []}}
    client, _ = _client(monkeypatch, response=_response(payload))

    assert client.get_mae_7d("SITE001") is None


def _horizon_payload(buckets: dict[str, str]):
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "__name__": "ml_prediction_mae_by_horizon",
                        "site": "SITE001",
                        "horizon_bucket": bucket,
                    },
                    "value": [1758470400, value],
                }
                for bucket, value in buckets.items()
            ],
        },
    }


def test_get_mae_by_horizon_parses_all_buckets(monkeypatch):
    client, mock_get = _client(
        monkeypatch,
        response=_response(_horizon_payload({"0-1h": "5.0", "1-3j": "22.5"})),
    )

    result = client.get_mae_by_horizon("SITE001")

    assert result == {"0-1h": 5.0, "1-3j": 22.5}
    mock_get.assert_called_once_with(
        "http://fake:9090/api/v1/query",
        params={"query": 'ml_prediction_mae_by_horizon{site="SITE001"}'},
        timeout=5.0,
    )


def test_get_mae_by_horizon_returns_empty_dict_when_metric_is_absent(monkeypatch):
    payload = {"status": "success", "data": {"resultType": "vector", "result": []}}
    client, _ = _client(monkeypatch, response=_response(payload))

    assert client.get_mae_by_horizon("SITE001") == {}


def test_get_mae_by_horizon_returns_empty_dict_when_prometheus_unreachable(monkeypatch):
    client, _ = _client(monkeypatch, raises=requests.ConnectionError("refused"))

    assert client.get_mae_by_horizon("SITE001") == {}
