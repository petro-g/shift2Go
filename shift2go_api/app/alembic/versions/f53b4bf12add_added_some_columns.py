"""added some columns

Revision ID: f53b4bf12add
Revises: 59934c7d6870
Create Date: 2021-10-08 07:40:45.230396-07:00

"""
from alembic import op
from sqlalchemy import DateTime, Column 

# revision identifiers, used by Alembic.
revision = 'f53b4bf12add'
down_revision = '59934c7d6870'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'shifts',
        Column("endedAt", DateTime)
    )


def downgrade():
    op.drop_column(
        table_name='shifts',
        column_name='endedAt'
    )
