"""bootstrap extension and schema

Revision ID: 0d230748d8a2
Revises:
Create Date: 2026-09-15 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0d230748d8a2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Remplace db/init/001-init-timescaledb.sql : ce bootstrap (extension
    timescaledb + schéma enervision) est désormais géré par Alembic comme
    le reste du schéma, plutôt que par un script exécuté une seule fois
    au premier démarrage de Postgres.
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE SCHEMA IF NOT EXISTS enervision")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA IF EXISTS enervision CASCADE")
    op.execute("DROP EXTENSION IF EXISTS timescaledb")
