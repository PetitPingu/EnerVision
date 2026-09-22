"""Tests d'intégration de SqlSiteRepository contre un vrai Postgres."""

import uuid

import pytest
from db_schema.models import Site as SiteRow

from infrastructure.session import get_session
from infrastructure.site_repository import SqlSiteRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def site_id():
    return f"INTEGRATION-TEST-{uuid.uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def _cleanup(site_id):
    yield
    with get_session() as session:
        session.query(SiteRow).filter(SiteRow.site_id == site_id).delete()
        session.commit()


def test_get_site_returns_site_with_capacity(site_id):
    with get_session() as session:
        session.add(SiteRow(site_id=site_id, site_name="Usine test", capacity_kw=250.0))
        session.commit()

    site = SqlSiteRepository().get_site(site_id)

    assert site is not None
    assert site.site_id == site_id
    assert site.capacity_kw == 250.0


def test_get_site_returns_none_when_capacity_kw_is_null(site_id):
    with get_session() as session:
        session.add(SiteRow(site_id=site_id, site_name="Usine test", capacity_kw=None))
        session.commit()

    assert SqlSiteRepository().get_site(site_id) is None


def test_get_site_returns_none_for_unknown_site():
    assert SqlSiteRepository().get_site("does-not-exist") is None
