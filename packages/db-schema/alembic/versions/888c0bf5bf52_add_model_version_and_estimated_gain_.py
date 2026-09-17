"""add model_version and estimated_gain_kwh to recommendations

Revision ID: 888c0bf5bf52
Revises: 32eacc6ca95f
Create Date: 2026-09-17 14:02:18.147548

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '888c0bf5bf52'
down_revision: Union[str, Sequence[str], None] = '32eacc6ca95f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "recommendations",
        sa.Column("model_version", sa.String(), nullable=True),
        schema="enervision",
    )
    op.add_column(
        "recommendations",
        sa.Column("estimated_gain_kwh", sa.Float(), nullable=True),
        schema="enervision",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("recommendations", "estimated_gain_kwh", schema="enervision")
    op.drop_column("recommendations", "model_version", schema="enervision")
