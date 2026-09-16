"""create readings curated

Revision ID: 49341887b86a
Revises: 63f02d95cce8
Create Date: 2026-09-16 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49341887b86a'
down_revision: Union[str, Sequence[str], None] = '63f02d95cce8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    `readings_curated` : sortie du job de transformation raw -> curated
    (apps/etl_worker/domain/imputation.py), prête à consommer comme
    feature pour l'entraînement de modèle. Une seule colonne par champ
    de mesure (sa valeur finale) ; `imputation_methods` (nullable)
    indique le sort de consumption_kwh (seul champ imputé) : None si
    connue, "forward_fill" si comblée, "no_history" si restée None
    faute d'historique.
    """
    op.create_table(
        "readings_curated",
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
            "imputation_methods",
            sa.String(),
            nullable=True,
        ),
        sa.Column(
            "null_reasons",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("data_quality", sa.String(), nullable=True),
        sa.Column(
            "curated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="enervision",
    )
    op.execute(
        "SELECT create_hypertable('enervision.readings_curated', 'timestamp', migrate_data => TRUE)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("readings_curated", schema="enervision")
