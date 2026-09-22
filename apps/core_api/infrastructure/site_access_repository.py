"""Implémentation SQL du SiteAccessPort (table `user_sites`, packages/db-schema)."""

import uuid

from application.ports import SiteAccessPort
from db_schema.models import UserSite as UserSiteRow

from .session import get_session


class SqlSiteAccessRepository(SiteAccessPort):
    """Lit/écrit les sites assignés à un utilisateur non-admin."""

    def get_site_ids(self, user_id: str) -> list[str]:
        with get_session() as session:
            rows = (
                session.query(UserSiteRow.site_id)
                .filter(UserSiteRow.user_id == uuid.UUID(user_id))
                .all()
            )
        return [row[0] for row in rows]

    def set_site_ids(self, user_id: str, site_ids: list[str]) -> None:
        user_uuid = uuid.UUID(user_id)
        with get_session() as session:
            session.query(UserSiteRow).filter(UserSiteRow.user_id == user_uuid).delete()
            session.add_all(
                [UserSiteRow(user_id=user_uuid, site_id=site_id) for site_id in site_ids]
            )
            session.commit()
