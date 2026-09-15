from unittest.mock import MagicMock, patch

from infrastructure.sites_writer import SitesWriter
from mockapi_client import Site


def _site(**overrides) -> Site:
    data = {
        "site_id": "SITE001",
        "site_type": "office",
        "site_name": "Bureau Paris",
        "location": "Paris, France",
        "capacity_kw": 200.0,
        "status": "active",
        **overrides,
    }
    return Site(**data)


def test_upsert_all_executes_one_statement_per_site():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    conn.__enter__.return_value = conn

    with patch("infrastructure.sites_writer.psycopg2.connect", return_value=conn):
        writer = SitesWriter(dsn="postgresql://fake")
        writer.upsert_all([_site(site_id="SITE001"), _site(site_id="SITE002")])

    assert cursor.execute.call_count == 2
    sql = cursor.execute.call_args_list[0][0][0]
    assert "ON CONFLICT (site_id) DO UPDATE" in sql
    conn.close.assert_called_once()


def test_upsert_all_with_no_sites_still_closes_connection():
    conn = MagicMock()
    conn.__enter__.return_value = conn

    with patch("infrastructure.sites_writer.psycopg2.connect", return_value=conn):
        writer = SitesWriter(dsn="postgresql://fake")
        writer.upsert_all([])

    conn.close.assert_called_once()
