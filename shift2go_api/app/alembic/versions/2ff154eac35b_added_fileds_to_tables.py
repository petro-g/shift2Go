"""added fileds to tables

Revision ID: 2ff154eac35b
Revises: 11a04be37413
Create Date: 2021-10-07 10:28:31.171786-07:00

"""
from alembic import op
from sqlalchemy import Column, String, Float

from app.config import constants


# revision identifiers, used by Alembic.
revision = '2ff154eac35b'
down_revision = '11a04be37413'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'notifications',
        Column("notificationType", String, default=constants.NOTIFICATION_BOTH)
    )
    op.add_column(
        "hotels",
        Column("longitude", Float, default=0.0),
    )
    op.add_column(
        "hotels",
        Column("latitude", Float, default=0.0),
    )


def downgrade():
    op.drop_column(
        table_name='notifications',
        column_name='notificationType'
    )
    op.drop_column(
        table_name='hotels',
        column_name='longitude'
    )
    op.drop_column(
        table_name='hotels',
        column_name='latitude'
    )
