"""add indexes on fault_record filtering columns

Revision ID: a1e3d2c4b5f6
Revises: cf05088a299f
Create Date: 2025-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1e3d2c4b5f6'
down_revision: Union[str, None] = 'cf05088a299f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes to speed up filtering on fault dashboard."""
    # SQLite supports CREATE INDEX; use Alembic helpers
    op.create_index('ix_fault_record_province_fault_type', 'fault_record', ['province_fault_type'], unique=False)
    op.create_index('ix_fault_record_cause_category', 'fault_record', ['cause_category'], unique=False)
    op.create_index('ix_fault_record_notification_level', 'fault_record', ['notification_level'], unique=False)
    op.create_index('ix_fault_record_fault_duration_hours', 'fault_record', ['fault_duration_hours'], unique=False)
    op.create_index('ix_fault_record_fault_date', 'fault_record', ['fault_date'], unique=False)


def downgrade() -> None:
    """Remove indexes added in upgrade."""
    op.drop_index('ix_fault_record_fault_date', table_name='fault_record')
    op.drop_index('ix_fault_record_fault_duration_hours', table_name='fault_record')
    op.drop_index('ix_fault_record_notification_level', table_name='fault_record')
    op.drop_index('ix_fault_record_cause_category', table_name='fault_record')
    op.drop_index('ix_fault_record_province_fault_type', table_name='fault_record')
