"""Implémentation SQL du SiteRepositoryPort (table `sites`, packages/db-schema)."""

from application.ports import SiteRepositoryPort
from db_schema.models import Site as SiteRow
from domain.entities import Site

from .session import get_session


class SqlSiteRepository(SiteRepositoryPort):
    """Lit les sites depuis la base partagée."""

    def get_site(self, site_id: str) -> Site | None:
        with get_session() as session:
            row = session.get(SiteRow, site_id)
        if row is None or row.capacity_kw is None:
            return None
        return Site(site_id=row.site_id, capacity_kw=row.capacity_kw)
