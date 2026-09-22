"""create predictions log table

Revision ID: 5d05eed9fc20
Revises: 888c0bf5bf52
Create Date: 2026-09-21 14:26:10.100186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5d05eed9fc20'
down_revision: Union[str, Sequence[str], None] = '888c0bf5bf52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    `predictions_log` : une ligne par appel à /predict (apps/prediction),
    écrite au moment de l'inférence. Sert de base au job de rapprochement
    de l'ETL worker (docs/monitoring_model.md) qui la joint plus tard à
    readings_curated sur (site_id, timestamp = target_timestamp) pour
    calculer l'erreur a posteriori. Pas de FK vers `sites` (même
    convention que readings_curated : site_id est un simple champ texte).
    """
    op.create_table(
        "predictions_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", sa.String(), nullable=False),
        sa.Column("target_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_consumption_kwh", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="enervision",
    )
    op.create_index(
        "ix_predictions_log_site_target",
        "predictions_log",
        ["site_id", "target_timestamp"],
        schema="enervision",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_predictions_log_site_target",
        table_name="predictions_log",
        schema="enervision",
    )
    op.drop_table("predictions_log", schema="enervision")
