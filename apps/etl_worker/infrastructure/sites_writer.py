"""Upsert des sites dans enervision.sites.

Nécessaire avant d'insérer dans enervision.readings, qui porte une clé
étrangère sur site_id (voir apps/core_api/infrastructure/orm_models.py).
"""

import psycopg2
from mockapi_client import Site

from .config import Config

_UPSERT_SQL = """
    INSERT INTO enervision.sites (site_id, site_name, site_type, location, capacity_kw, status)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (site_id) DO UPDATE SET
        site_name = EXCLUDED.site_name,
        site_type = EXCLUDED.site_type,
        location = EXCLUDED.location,
        capacity_kw = EXCLUDED.capacity_kw,
        status = EXCLUDED.status
"""


class SitesWriter:
    """Maintient enervision.sites à jour à partir des sites de l'API mock."""

    def __init__(self, dsn: str | None = None):
        self._dsn = dsn or Config.DATABASE_URL

    def upsert_all(self, sites: list[Site]) -> None:
        conn = psycopg2.connect(self._dsn)
        try:
            with conn:
                with conn.cursor() as cur:
                    for site in sites:
                        cur.execute(
                            _UPSERT_SQL,
                            (
                                site.site_id,
                                site.site_name,
                                site.site_type,
                                site.location,
                                site.capacity_kw,
                                site.status,
                            ),
                        )
        finally:
            conn.close()
