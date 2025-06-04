"""register notifications table

Revision ID: 5c44786b0f93
Revises: 511f432a6f92
Create Date: 2025-06-03 21:19:04.321540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c44786b0f93'
down_revision: Union[str, None] = '511f432a6f92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
