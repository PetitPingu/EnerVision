"""merge_readings_and_recommendations_heads

Revision ID: 32eacc6ca95f
Revises: a0c14d348753, a3f6e1c9d2b7
Create Date: 2026-09-17 09:59:06.267606

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32eacc6ca95f'
down_revision: Union[str, Sequence[str], None] = ('a0c14d348753', 'a3f6e1c9d2b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
