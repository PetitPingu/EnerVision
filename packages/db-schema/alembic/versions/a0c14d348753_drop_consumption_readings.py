"""drop consumption readings

Revision ID: a0c14d348753
Revises: 49341887b86a
Create Date: 2026-09-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0c14d348753'
down_revision: Union[str, Sequence[str], None] = '49341887b86a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    `consumption_readings` n'a jamais été alimentée : c'était la cible
    prévue du Worker ETL avant qu'on construise `readings_curated`
    (EtlJob -> ConsumptionKwhImputer), qui a pris ce rôle avec un besoin
    différent (valeur comblée par champ, prête pour l'entraînement).
    Aucun code du repo n'écrit ni ne lit `consumption_readings`.
    """
    op.drop_table("consumption_readings", schema="enervision")


def downgrade() -> None:
    """Downgrade schema."""
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
    op.execute(
        "SELECT create_hypertable('enervision.consumption_readings', 'timestamp', migrate_data => TRUE)"
    )
