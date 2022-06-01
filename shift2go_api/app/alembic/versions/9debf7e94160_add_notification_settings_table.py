"""add notification settings table

Revision ID: 9debf7e94160
Revises: 156fab117915
Create Date: 2021-10-06 23:11:22.568788-07:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey,
                        Integer)
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '9debf7e94160'
down_revision = '156fab117915'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notification_settings',
        Column("id", Integer, primary_key=True, index=True),
        Column("push", Boolean, default=True),
        Column("email", Boolean, default=True),
        Column("createdBy", Integer, ForeignKey('users.id'), nullable=False),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )


def downgrade():
    op.drop_table('notification_settings')
