from unittest.mock import Mock

from domain.entities import User
from fastapi.testclient import TestClient
from infrastructure.auth import create_access_token, hash_password
from infrastructure.login_throttle import MAX_ATTEMPTS, reset_attempts
from presentation import api


def _client_with_user(monkeypatch, user=None):
    mock_repo = Mock()
    mock_repo.get_by_email.return_value = user
    monkeypatch.setattr(api, "user_repository", mock_repo)
    return TestClient(api.app), mock_repo


def test_login_returns_token_for_valid_credentials(monkeypatch):
    user = User(id="1", email="alice@example.com", password_hash=hash_password("s3cret"))
    client, _ = _client_with_user(monkeypatch, user=user)

    response = client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "s3cret"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_returns_401_for_wrong_password(monkeypatch):
    user = User(id="1", email="alice@example.com", password_hash=hash_password("s3cret"))
    client, _ = _client_with_user(monkeypatch, user=user)

    response = client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong"}
    )

    assert response.status_code == 401


def test_login_returns_401_for_unknown_email(monkeypatch):
    client, _ = _client_with_user(monkeypatch, user=None)

    response = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever"}
    )

    assert response.status_code == 401


def test_login_locks_out_after_too_many_failed_attempts(monkeypatch):
    email = "throttled-test-user@example.com"
    reset_attempts(email)  # isolation si ce test tourne plusieurs fois dans le même process

    user = User(id="1", email=email, password_hash=hash_password("correct-password-1"))
    client, _ = _client_with_user(monkeypatch, user=user)

    for _ in range(MAX_ATTEMPTS):
        response = client.post("/auth/login", json={"email": email, "password": "wrong"})
        assert response.status_code == 401

    locked_response = client.post(
        "/auth/login", json={"email": email, "password": "correct-password-1"}
    )

    assert locked_response.status_code == 429
    reset_attempts(email)


def test_protected_route_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(api, "sensor_api", Mock(get_sites=Mock(return_value=[])))

    client = TestClient(api.app)
    response = client.get("/api/v1/sites")

    assert response.status_code == 401


def test_protected_route_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(api, "sensor_api", Mock(get_sites=Mock(return_value=[])))

    client = TestClient(api.app)
    response = client.get(
        "/api/v1/sites", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


def test_protected_route_accepts_valid_token(monkeypatch):
    monkeypatch.setattr(api, "sensor_api", Mock(get_sites=Mock(return_value=[])))

    client = TestClient(api.app)
    token = create_access_token("alice@example.com")
    response = client.get("/api/v1/sites", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
