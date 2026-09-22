"""Tests d'intégration de SqlUserRepository contre un vrai Postgres."""

import uuid

import pytest

from infrastructure.session import get_session
from infrastructure.user_repository import SqlUserRepository

pytestmark = pytest.mark.integration


def _email(suffix: str) -> str:
    return f"integration-test-{suffix}-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def repo():
    return SqlUserRepository()


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    from db_schema.models import User as UserRow

    with get_session() as session:
        session.query(UserRow).filter(UserRow.email.like("integration-test-%")).delete(
            synchronize_session=False
        )
        session.commit()


def test_create_then_get_by_email_round_trips(repo):
    email = _email("create")
    created = repo.create(email, "hashed-pw", "viewer")

    found = repo.get_by_email(email)

    assert found is not None
    assert found.id == created.id
    assert found.role == "viewer"


def test_create_duplicate_email_raises_value_error(repo):
    email = _email("dup")
    repo.create(email, "hashed-pw", "viewer")

    with pytest.raises(ValueError):
        repo.create(email, "another-hash", "viewer")


def test_get_by_id_returns_none_for_unknown_user(repo):
    assert repo.get_by_id(str(uuid.uuid4())) is None


def test_update_role_persists_change(repo):
    created = repo.create(_email("role"), "hashed-pw", "viewer")

    updated = repo.update_role(created.id, "admin")

    assert updated.role == "admin"
    assert repo.get_by_id(created.id).role == "admin"


def test_update_role_returns_none_for_unknown_user(repo):
    assert repo.update_role(str(uuid.uuid4()), "admin") is None


def test_delete_removes_user(repo):
    created = repo.create(_email("delete"), "hashed-pw", "viewer")

    deleted = repo.delete(created.id)

    assert deleted is True
    assert repo.get_by_id(created.id) is None


def test_delete_returns_false_for_unknown_user(repo):
    assert repo.delete(str(uuid.uuid4())) is False


def test_list_all_includes_created_user(repo):
    email = _email("list")
    repo.create(email, "hashed-pw", "viewer")

    emails = [u.email for u in repo.list_all()]

    assert email in emails
