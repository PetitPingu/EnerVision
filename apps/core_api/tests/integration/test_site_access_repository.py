"""Tests d'intégration de SqlSiteAccessRepository contre un vrai Postgres."""

import uuid

import pytest
from db_schema.models import Site as SiteRow
from db_schema.models import User as UserRow
from db_schema.models import UserSite as UserSiteRow

from infrastructure.session import get_session
from infrastructure.site_access_repository import SqlSiteAccessRepository
from infrastructure.user_repository import SqlUserRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def repo():
    return SqlSiteAccessRepository()


@pytest.fixture
def site_ids():
    ids = [f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}" for _ in range(2)]
    with get_session() as session:
        session.add_all(SiteRow(site_id=sid, site_name="Site de test") for sid in ids)
        session.commit()

    yield ids

    # Nettoie d'abord les affectations (user_sites) qui référencent ces
    # sites : l'ordre de teardown des fixtures n'est pas garanti par
    # rapport à `user_id`, cette suppression est donc auto-suffisante.
    with get_session() as session:
        session.query(UserSiteRow).filter(UserSiteRow.site_id.in_(ids)).delete(
            synchronize_session=False
        )
        session.query(SiteRow).filter(SiteRow.site_id.in_(ids)).delete(synchronize_session=False)
        session.commit()


@pytest.fixture
def user_id():
    created = SqlUserRepository().create(
        f"integration-test-site-access-{uuid.uuid4().hex[:8]}@example.com", "hashed-pw", "viewer"
    )

    yield created.id

    with get_session() as session:
        session.query(UserRow).filter(UserRow.id == uuid.UUID(created.id)).delete()
        session.commit()


def test_set_then_get_site_ids_round_trips(repo, user_id, site_ids):
    repo.set_site_ids(user_id, site_ids)

    assert sorted(repo.get_site_ids(user_id)) == sorted(site_ids)


def test_set_site_ids_replaces_previous_assignment(repo, user_id, site_ids):
    repo.set_site_ids(user_id, site_ids)

    repo.set_site_ids(user_id, [site_ids[0]])

    assert repo.get_site_ids(user_id) == [site_ids[0]]


def test_get_site_ids_returns_empty_list_for_user_without_access(repo, user_id):
    assert repo.get_site_ids(user_id) == []
