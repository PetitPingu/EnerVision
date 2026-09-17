from unittest.mock import Mock

import requests
from infrastructure.recommendation_client import RecommendationApiClient


def _client(monkeypatch, response=None, raises=None):
    mock_get = Mock()
    if raises is not None:
        mock_get.side_effect = raises
    else:
        mock_get.return_value = response
    monkeypatch.setattr(requests, "get", mock_get)
    return RecommendationApiClient(base_url="http://fake:8003"), mock_get


def _response(json_data, status_ok=True):
    response = Mock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("boom")
    return response


def test_get_recommendations_relays_the_service_response(monkeypatch):
    client, mock_get = _client(
        monkeypatch,
        response=_response([{"site_id": "SITE001", "action": "load_shifting"}]),
    )

    result = client.get_recommendations("SITE001")

    assert result == [{"site_id": "SITE001", "action": "load_shifting"}]
    mock_get.assert_called_once_with(
        "http://fake:8003/api/v1/recommendations",
        params={"site_id": "SITE001"},
        timeout=5.0,
    )


def test_get_recommendations_returns_none_on_http_error(monkeypatch, caplog):
    client, _ = _client(monkeypatch, response=_response({}, status_ok=False))

    with caplog.at_level("ERROR"):
        result = client.get_recommendations("SITE001")

    assert result is None
    assert "Échec de l'appel au service recommendation" in caplog.text


def test_get_recommendations_returns_none_when_service_unreachable(monkeypatch):
    client, _ = _client(monkeypatch, raises=requests.ConnectionError("refused"))

    result = client.get_recommendations("SITE001")

    assert result is None
