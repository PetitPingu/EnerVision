"""merge predictions_log and users heads

Revision ID: 7e1b3baf230d
Revises: 5d05eed9fc20, 98e291945145
Create Date: 2026-09-21 17:07:12.756123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e1b3baf230d'
down_revision: Union[str, Sequence[str], None] = ('5d05eed9fc20', '98e291945145')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
