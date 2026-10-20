"""empty message

Revision ID: d67c6981a1c5
Revises: 5c44786b0f93
Create Date: 2025-06-04 16:28:21.739045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd67c6981a1c5'
down_revision: Union[str, None] = '5c44786b0f93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
