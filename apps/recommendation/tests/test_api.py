from dataclasses import asdict
from unittest.mock import Mock

from domain.entities import Recommendation
from fastapi.testclient import TestClient
from presentation import api

RECOMMENDATIONS = [
    Recommendation(site_id="SITE001", type="load_shedding", message="Effacement recommandé.")
]


def _client(monkeypatch, recommendations=RECOMMENDATIONS):
    mock_use_case = Mock()
    mock_use_case.execute.return_value = recommendations
    monkeypatch.setattr(api, "generate_recommendations", mock_use_case)
    return TestClient(api.app), mock_use_case


def test_root_lists_endpoints(monkeypatch):
    client, _ = _client(monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "/recommendations" in response.json()["endpoints"]


def test_health_returns_ok(monkeypatch):
    client, _ = _client(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommendations_relays_use_case_result(monkeypatch):
    client, mock_use_case = _client(monkeypatch)

    response = client.get("/recommendations", params={"site_id": "SITE001"})

    assert response.status_code == 200
    assert response.json() == [asdict(r) for r in RECOMMENDATIONS]
    mock_use_case.execute.assert_called_once_with("SITE001")


def test_recommendations_returns_404_when_site_or_prediction_unavailable(monkeypatch):
    client, _ = _client(monkeypatch, recommendations=None)

    response = client.get("/recommendations", params={"site_id": "SITE404"})

    assert response.status_code == 404


def test_recommendations_requires_site_id(monkeypatch):
    client, _ = _client(monkeypatch)

    response = client.get("/recommendations")

    assert response.status_code == 422
