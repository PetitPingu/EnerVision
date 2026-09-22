"""create core tables

Revision ID: 88f8b0c0d047
Revises: 
Create Date: 2026-09-15 14:30:19.927514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88f8b0c0d047'
down_revision: Union[str, Sequence[str], None] = '0d230748d8a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sites",
        sa.Column("site_id", sa.String(), primary_key=True),
        sa.Column("site_name", sa.String(), nullable=True),
        sa.Column("site_type", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("capacity_kw", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        schema="enervision",
    )

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
    # `timestamp` doit faire partie de la clé de partitionnement TimescaleDB :
    # migrate_data=True convertit la table déjà créée (vide ici) en hypertable.
    op.execute(
        "SELECT create_hypertable('enervision.readings', 'timestamp', migrate_data => TRUE)"
    )

    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "site_id",
            sa.String(),
            sa.ForeignKey("enervision.sites.site_id"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        schema="enervision",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("alerts", schema="enervision")
    op.drop_table("readings", schema="enervision")
    op.drop_table("sites", schema="enervision")
