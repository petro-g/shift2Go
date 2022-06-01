"""added notificaion object to hotel

Revision ID: 11a04be37413
Revises: 9debf7e94160
Create Date: 2021-10-07 00:31:16.860817-07:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, JSON

# revision identifiers, used by Alembic.
revision = '11a04be37413'
down_revision = '9debf7e94160'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'hotels',
        Column("notification", JSON, default={
            'email': True,
            'push': True
        })
    )


def downgrade():
    op.drop_column(
        table_name='hotels',
        column_name='notification'
    )
