"""merge heads

Revision ID: f6e5d4c3b2a1
Revises: a1e3d2c4b5f6, add_pue_drill_down
Create Date: 2025-08-20 16:26:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f6e5d4c3b2a1'
down_revision: Union[str, tuple[str, ...], None] = ('a1e3d2c4b5f6', 'add_pue_drill_down')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is a merge migration; no schema changes required.
    pass


def downgrade() -> None:
    # This merge has no structural changes to undo.
    pass
