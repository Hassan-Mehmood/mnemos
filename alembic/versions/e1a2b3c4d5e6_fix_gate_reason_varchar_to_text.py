"""fix gate_reason varchar(100) to unbounded text

Revision ID: e1a2b3c4d5e6
Revises: bca117653a9f
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'bca117653a9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'memory_log',
        'gate_reason',
        type_=sa.Text(),
        existing_type=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'memory_log',
        'gate_reason',
        type_=sa.String(length=100),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
