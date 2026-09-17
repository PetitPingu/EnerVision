from unittest.mock import Mock

import requests
from domain.entities import Prediction
from infrastructure.prediction_client import PredictionHttpClient


def _client(monkeypatch, response=None, raises=None):
    mock_get = Mock()
    if raises is not None:
        mock_get.side_effect = raises
    else:
        mock_get.return_value = response
    monkeypatch.setattr(requests, "get", mock_get)
    return PredictionHttpClient(base_url="http://prediction:8000"), mock_get


def _response(json_data, status_ok=True):
    response = Mock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("boom")
    return response


def test_get_prediction_calls_predict_endpoint_with_site_id_and_timestamp(monkeypatch):
    client, mock_get = _client(
        monkeypatch,
        response=_response({"site_id": "SITE001", "predicted_consumption_kwh": 120.0}),
    )

    result = client.get_prediction("SITE001")

    assert result == Prediction(site_id="SITE001", predicted_consumption_kw=120.0)
    _, kwargs = mock_get.call_args
    assert mock_get.call_args[0] == ("http://prediction:8000/predict",)
    assert kwargs["params"]["site_id"] == "SITE001"
    assert "timestamp" in kwargs["params"]
    assert kwargs["timeout"] == 5.0


def test_get_prediction_returns_none_on_http_error(monkeypatch):
    client, _ = _client(monkeypatch, response=_response({}, status_ok=False))

    assert client.get_prediction("SITE001") is None


def test_get_prediction_returns_none_when_service_unreachable(monkeypatch):
    client, _ = _client(monkeypatch, raises=requests.ConnectionError("refused"))

    assert client.get_prediction("SITE001") is None


def test_get_prediction_returns_none_on_unexpected_payload(monkeypatch):
    client, _ = _client(monkeypatch, response=_response({"unexpected": "shape"}))

    assert client.get_prediction("SITE001") is None
