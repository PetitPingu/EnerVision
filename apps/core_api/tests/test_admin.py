import uuid
from unittest.mock import Mock

from domain.entities import User
from fastapi.testclient import TestClient
from presentation import api


def _client(monkeypatch, as_role="admin", user_repo=None, site_access_repo=None):
    mock_user_repo = user_repo if user_repo is not None else Mock()
    mock_site_access_repo = site_access_repo if site_access_repo is not None else Mock()
    mock_site_access_repo.get_site_ids.return_value = []
    monkeypatch.setattr(api, "user_repository", mock_user_repo)
    monkeypatch.setattr(api, "site_access_repository", mock_site_access_repo)

    monkeypatch.setitem(
        api.app.dependency_overrides,
        api.require_auth,
        lambda: api.CurrentUser(email="admin@example.com", role=as_role, user_id="me-id"),
    )

    return TestClient(api.app), mock_user_repo, mock_site_access_repo


def test_non_admin_cannot_list_users(monkeypatch):
    client, _, _ = _client(monkeypatch, as_role="viewer")

    response = client.get("/admin/users")

    assert response.status_code == 403


def test_admin_can_list_users(monkeypatch):
    users = [
        User(id="1", email="alice@example.com", password_hash="x", role="admin"),
        User(id="2", email="bob@example.com", password_hash="x", role="viewer"),
    ]
    client, mock_user_repo, mock_site_access_repo = _client(monkeypatch)
    mock_user_repo.list_all.return_value = users
    mock_site_access_repo.get_site_ids.return_value = ["SITE001"]

    response = client.get("/admin/users")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["email"] == "alice@example.com"
    assert body[0]["site_ids"] == []  # admin: pas de filtrage stocké
    assert body[1]["email"] == "bob@example.com"
    assert body[1]["site_ids"] == ["SITE001"]


def test_admin_can_create_user(monkeypatch):
    client, mock_user_repo, mock_site_access_repo = _client(monkeypatch)
    mock_user_repo.create.return_value = User(
        id="3", email="carol@example.com", password_hash="x", role="viewer"
    )

    response = client.post(
        "/admin/users",
        json={
            "email": "carol@example.com",
            "password": "s3cretpass123",
            "role": "viewer",
            "site_ids": ["SITE001", "SITE002"],
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "carol@example.com"
    mock_site_access_repo.set_site_ids.assert_called_once_with("3", ["SITE001", "SITE002"])


def test_admin_create_user_rejects_weak_password(monkeypatch):
    client, mock_user_repo, _ = _client(monkeypatch)

    response = client.post(
        "/admin/users",
        json={"email": "carol@example.com", "password": "short"},
    )

    assert response.status_code == 422
    mock_user_repo.create.assert_not_called()


def test_admin_create_user_conflict_on_existing_email(monkeypatch):
    client, mock_user_repo, _ = _client(monkeypatch)
    mock_user_repo.create.side_effect = ValueError("Un utilisateur existe déjà avec cet email")

    response = client.post(
        "/admin/users",
        json={"email": "dup@example.com", "password": "s3cretpass123"},
    )

    assert response.status_code == 409


def test_admin_cannot_remove_their_own_admin_role(monkeypatch):
    client, mock_user_repo, _ = _client(monkeypatch)
    mock_user_repo.get_by_id.return_value = User(
        id="me-id", email="admin@example.com", password_hash="x", role="admin"
    )

    response = client.patch("/admin/users/me-id", json={"role": "viewer"})

    assert response.status_code == 400
    mock_user_repo.update_role.assert_not_called()


def test_admin_can_update_another_users_role_and_sites(monkeypatch):
    client, mock_user_repo, mock_site_access_repo = _client(monkeypatch)
    mock_user_repo.get_by_id.return_value = User(
        id="2", email="bob@example.com", password_hash="x", role="viewer"
    )
    mock_user_repo.update_role.return_value = User(
        id="2", email="bob@example.com", password_hash="x", role="admin"
    )

    response = client.patch(
        "/admin/users/2", json={"role": "admin", "site_ids": ["SITE003"]}
    )

    assert response.status_code == 200
    mock_user_repo.update_role.assert_called_once_with("2", "admin")
    mock_site_access_repo.set_site_ids.assert_called_once_with("2", ["SITE003"])


def test_admin_update_returns_404_for_unknown_user(monkeypatch):
    client, mock_user_repo, _ = _client(monkeypatch)
    mock_user_repo.get_by_id.return_value = None

    response = client.patch(f"/admin/users/{uuid.uuid4()}", json={"role": "admin"})

    assert response.status_code == 404


def test_admin_cannot_delete_their_own_account(monkeypatch):
    client, mock_user_repo, _ = _client(monkeypatch)
    mock_user_repo.get_by_id.return_value = User(
        id="me-id", email="admin@example.com", password_hash="x", role="admin"
    )

    response = client.delete("/admin/users/me-id")

    assert response.status_code == 400
    mock_user_repo.delete.assert_not_called()


def test_admin_can_delete_another_user(monkeypatch):
    client, mock_user_repo, _ = _client(monkeypatch)
    mock_user_repo.get_by_id.return_value = User(
        id="2", email="bob@example.com", password_hash="x", role="viewer"
    )
    mock_user_repo.delete.return_value = True

    response = client.delete("/admin/users/2")

    assert response.status_code == 200
    mock_user_repo.delete.assert_called_once_with("2")


def test_admin_delete_returns_404_for_unknown_user(monkeypatch):
    client, mock_user_repo, _ = _client(monkeypatch)
    mock_user_repo.get_by_id.return_value = None

    response = client.delete(f"/admin/users/{uuid.uuid4()}")

    assert response.status_code == 404
