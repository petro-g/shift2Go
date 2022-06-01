"""added confirmed to shift

Revision ID: 32aea683d933
Revises: 3cb1263a0f82
Create Date: 2021-11-29 23:42:34.179669-08:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32aea683d933'
down_revision = '3cb1263a0f82'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('shifts', sa.Column('confirmed', sa.Boolean(), nullable=True, default=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('shifts', 'confirmed')
    # ### end Alembic commands ###