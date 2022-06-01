"""more columns

Revision ID: cc84cd122b5c
Revises: f53b4bf12add
Create Date: 2021-10-08 11:00:42.349541-07:00

"""
from alembic import op
from sqlalchemy import Column, String


# revision identifiers, used by Alembic.
revision = 'cc84cd122b5c'
down_revision = 'f53b4bf12add'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_roles",
        Column("image", String, default='www.google.com')
    )
    op.add_column(
        "certificates",
        Column("url", String, default='www.google.com')
    )
    op.add_column(
        "hotels",
        Column("address", String)
    )
    op.alter_column(
        table_name='shift_cancellations',
        column_name="reason",
        nullable=True
    )
    op.alter_column(
        table_name='users',
        column_name="phone",
        nullable=True
    )
    op.alter_column(
        table_name='users',
        column_name="address",
        nullable=True
    )



def downgrade():
    op.drop_column(
        table_name="job_roles",
        column_name='image'
    )
    op.drop_column(
        table_name="certificates",
        column_name='url'
    )
    op.drop_column(
        table_name="hotels",
        column_name='address'
    )
    op.alter_column(
        table_name='shift_cancellations',
        nullable=False
    )
