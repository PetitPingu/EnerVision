"""create user_sites table

Revision ID: 98e291945145
Revises: c54505b1fc62
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '98e291945145'
down_revision: Union[str, Sequence[str], None] = 'c54505b1fc62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_sites",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enervision.users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "site_id",
            sa.String(),
            sa.ForeignKey("enervision.sites.site_id"),
            primary_key=True,
        ),
        schema="enervision",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("user_sites", schema="enervision")
