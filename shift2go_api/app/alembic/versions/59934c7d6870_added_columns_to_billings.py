"""added columns to billings

Revision ID: 59934c7d6870
Revises: 2ff154eac35b
Create Date: 2021-10-07 15:34:20.964924-07:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String, Float


# revision identifiers, used by Alembic.
revision = '59934c7d6870'
down_revision = '2ff154eac35b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'billings',
        Column("amountPayableToShift2go", Float)
    )
    op.add_column(
        "billings",
        Column("amountPayableToContractor", Float, default=0.0),
    )



def downgrade():
    op.drop_column(
        table_name='billings',
        column_name='amountPayableToShift2go'
    )
 
    op.drop_column(
        table_name='billings',
        column_name='amountPayableToContractor'
    )
 
