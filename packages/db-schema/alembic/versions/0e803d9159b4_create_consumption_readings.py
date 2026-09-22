"""create consumption readings

Revision ID: 0e803d9159b4
Revises: 88f8b0c0d047
Create Date: 2026-09-15 16:03:27.921791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e803d9159b4'
down_revision: Union[str, Sequence[str], None] = '88f8b0c0d047'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "consumption_readings",
        sa.Column("site_id", sa.String(), primary_key=True),
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
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="enervision",
    )
    # `timestamp` doit faire partie de la clé de partitionnement TimescaleDB :
    # migrate_data=True convertit la table déjà créée (vide ici) en hypertable.
    op.execute(
        "SELECT create_hypertable('enervision.consumption_readings', 'timestamp', migrate_data => TRUE)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("consumption_readings", schema="enervision")
