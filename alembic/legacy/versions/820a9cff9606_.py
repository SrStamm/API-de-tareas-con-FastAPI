"""empty message

Revision ID: 820a9cff9606
Revises: 7a739d51991b, d67c6981a1c5
Create Date: 2025-06-04 16:35:58.573757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '820a9cff9606'
down_revision: Union[str, None] = ('7a739d51991b', 'd67c6981a1c5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
