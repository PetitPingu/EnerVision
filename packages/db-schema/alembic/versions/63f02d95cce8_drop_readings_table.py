"""drop readings table

Revision ID: 63f02d95cce8
Revises: 0e803d9159b4
Create Date: 2026-09-15 18:17:36.827850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63f02d95cce8'
down_revision: Union[str, Sequence[str], None] = '0e803d9159b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    `readings` faisait doublon avec `consumption_readings` (même grain,
    mêmes colonnes de mesure) : deux tickets distincts ont créé une table
    de lectures structurées sans se coordonner. On garde une seule table
    (`consumption_readings`, alimentée par le worker ETL depuis le data
    lake MinIO) plutôt que de synchroniser `sites` pour honorer la FK de
    `readings`, qui restait de toute façon vide.
    """
    op.drop_table("readings", schema="enervision")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "readings",
        sa.Column(
            "site_id",
            sa.String(),
            sa.ForeignKey("enervision.sites.site_id"),
            primary_key=True,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("site_type", sa.String(), nullable=True),
        sa.Column("consumption_kw", sa.Float(), nullable=True),
        sa.Column("consumption_kwh", sa.Float(), nullable=True),
        sa.Column("voltage_v", sa.Float(), nullable=True),
        sa.Column("current_a", sa.Float(), nullable=True),
        sa.Column("power_factor", sa.Float(), nullable=True),
        sa.Column("temperature_celsius", sa.Float(), nullable=True),
        sa.Column("humidity_percent", sa.Float(), nullable=True),
        sa.Column(
            "null_reasons",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("data_quality", sa.String(), nullable=True),
        schema="enervision",
    )
    op.execute(
        "SELECT create_hypertable('enervision.readings', 'timestamp', migrate_data => TRUE)"
    )
