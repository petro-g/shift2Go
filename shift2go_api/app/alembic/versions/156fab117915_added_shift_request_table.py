"""added shift request table

Revision ID: 156fab117915
Revises: d55905fd5cbc
Create Date: 2021-10-01 15:35:02.178733-07:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Time, and_)
from sqlalchemy.orm import relationship
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '156fab117915'
down_revision = 'd55905fd5cbc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shift_request",
        Column("id", Integer, primary_key=True, index=True),
        Column("notes", String),
        Column("shift_id", Integer, ForeignKey('shifts.id'), nullable=False),
        Column("createdBy", Integer, ForeignKey('users.id'), nullable=False),
        Column("accepted", Boolean, default=False),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )


def downgrade():
    op.drop_table("shift_requests")
