"""upate notification_settings table

Revision ID: b4e3c857c641
Revises: c2cda0fa38ee
Create Date: 2021-10-25 07:35:40.759460-07:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4e3c857c641'
down_revision = 'c2cda0fa38ee'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('notification_settings', sa.Column('reminder', sa.Integer(), nullable=True, default=1))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('notification_settings', 'reminder')
    # ### end Alembic commands ###
