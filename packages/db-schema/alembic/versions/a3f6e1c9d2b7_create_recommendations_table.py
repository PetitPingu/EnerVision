"""create recommendations table

Revision ID: a3f6e1c9d2b7
Revises: 63f02d95cce8
Create Date: 2026-09-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3f6e1c9d2b7'
down_revision: Union[str, Sequence[str], None] = '63f02d95cce8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "site_id",
            sa.String(),
            sa.ForeignKey("enervision.sites.site_id"),
            nullable=False,
        ),
        # Pas de FK vers `predictions` : cette table n'existe pas encore
        # (voir docs/archi_database.md, PREDICTIONS reste "proposé").
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="enervision",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("recommendations", schema="enervision")
