"""creating database models

Revision ID: d55905fd5cbc
Revises: 
Create Date: 2021-10-01 07:31:01.153794-07:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Time, and_)
from sqlalchemy.orm import relationship
from datetime import datetime
# revision identifiers, used by Alembic.
revision = 'd55905fd5cbc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "countries",
        Column("code", String(2), primary_key=True,
               index=True, nullable=False),
        Column("name", String, nullable=False),
    )
    op.create_table(
        "users",
        Column("id", Integer, primary_key=True, index=True),
        Column("firstname", String, nullable=False),
        Column("lastname", String, nullable=False),
        Column("email", String, nullable=False),
        Column("hashed_password", String, nullable=False),
        Column("countryCode", String, ForeignKey('countries.code')),
        Column("phone", String, nullable=False),
        Column("latitude", Float),
        Column("longitude", Float),
        Column("userType", String, nullable=False),
        Column("address", String, nullable=False),
        Column("is_verified", Boolean, default=False),
        Column("is_active", Boolean, default=True),
        Column("is_superuser", Boolean, default=False),
        Column("deviceTokens", ARRAY(String)),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "bank_informations",
        Column("id", Integer, primary_key=True, index=True),
        Column("createdBy", Integer, ForeignKey("users.id")),
        Column("name", String, nullable=False),
        Column("accountNumber", String, nullable=False),
        Column("routingNumber", String, nullable=False),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "badges",
        Column("id", Integer, primary_key=True, index=True),
        Column("createdBy", Integer, ForeignKey("users.id")),
        Column("name", String, nullable=False),
        Column("image", String, nullable=True),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "contractors",
        Column("id", Integer, primary_key=True, index=True),
        Column("userID", Integer, ForeignKey('users.id'), nullable=False),
        Column("profilePicture", String),
        Column("rating", Float),
        Column("bank_id", Integer, ForeignKey('bank_informations.id')),
        Column("completedShiftsCount", Integer),
        Column("badges", ARRAY(Integer)),
        Column("verified", Boolean, default=False),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
        Column("jobRoles", ARRAY(Integer)),
        Column("certificate_ids", ARRAY(Integer)),
    )
    op.create_table(
        "hotel_admins",
        Column("id", Integer, primary_key=True, index=True),
        Column("userID", Integer, ForeignKey('users.id'), nullable=False),
        Column("profilePicture", String),
        Column("rating", Float),
        Column("verified", Boolean, default=False),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "hotels",
        Column("id", Integer, primary_key=True, index=True),
        Column("createdBy", Integer, ForeignKey('users.id'), nullable=False),
        Column("hotelAdmin", Integer, ForeignKey(
            'hotel_admins.id'), nullable=False),
        Column("name", String, nullable=False),
        Column("phone", String, nullable=False),
        Column("employerIdentificationNumber", String),
        Column("bank_id", Integer, ForeignKey('bank_informations.id')),
        Column("pictures", ARRAY(String)),
        Column("favouriteContractors", ARRAY(Integer)),
        Column("contractorsRadius", Float, default=20),
        Column("rating", Float),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "admins",
        Column("id", Integer, primary_key=True, index=True),
        Column("userID", Integer, ForeignKey('users.id'), nullable=False),
        Column("profilePicture", String),
        Column("rating", Float),
        Column("verified", Boolean, default=False),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "shifts",
        Column("id", Integer, primary_key=True, index=True),
        Column("name", String, nullable=False),
        Column("hotel_id", Integer, ForeignKey('hotels.id'), nullable=False),
        Column("roles_ids", ARRAY(Integer)),
        Column("pay", Float, nullable=False),
        Column("startTime", DateTime, nullable=False),
        Column("endTime", DateTime, nullable=False),
        Column("startedAt", DateTime),
        Column("instructions", String),
        Column("requiredCertificates", ARRAY(Integer)),
        Column("targetAudience", ARRAY(Integer)),
        Column("requests", ARRAY(Integer)),
        Column("audienceType", String, default='MARKET'),
        Column("clockInLatitude", Float),
        Column("clockOutLatitude", Float),
        Column("clockInLongitude", Float),
        Column("clockOutLongitude", Float),
        Column("status", String, default='PENDING'),
        Column("active", Boolean, default=True),
        Column("contractor_id", Integer, ForeignKey('contractors.id')),
        Column("createdBy", Integer, ForeignKey('users.id')),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "shift_cancellations",
        Column("id", Integer, primary_key=True, index=True),
        Column("shift_id", Integer, ForeignKey('shifts.id')),
        Column("reason", String, nullable=False),
        Column("cancelledBy", Integer, ForeignKey('users.id')),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "billings",
        Column("id", Integer, primary_key=True, index=True),
        Column("shift_id", Integer, ForeignKey('shifts.id')),
        Column("hotel_id", Integer, ForeignKey('hotels.id')),
        Column("status", String),
        Column("createdBy", Integer, ForeignKey('users.id')),
        Column("paymentTransactionID", String),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "notifications",
        Column("id", Integer, primary_key=True, index=True),
        Column("title", String),
        Column("message", String),
        Column("receivers", ARRAY(Integer)),
        Column("createdBy", Integer, ForeignKey('users.id')),
        Column("readBy", ARRAY(Integer)),
        Column("failed", ARRAY(Integer)),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        "job_roles",
        Column("id", Integer, primary_key=True, index=True),
        Column("name", String, nullable=False),
        Column("createdBy", Integer, ForeignKey('users.id')),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        'certificates',
        Column("id", Integer, primary_key=True, index=True),
        Column("name", String, nullable=False),
        Column("createdBy", Integer, ForeignKey('users.id')),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),

    )
    op.create_table(
        'reviews',
        Column("id", Integer, primary_key=True, index=True),
        Column("shift_id", Integer, ForeignKey('shifts.id')),
        Column("reviewee_id", Integer),  # HOTEL_ID or USER_ID,
        Column("reviewee_type", String),  # HOTEL or USER,
        Column("reviewer", Integer, ForeignKey('users.id')),
        Column("comment", String, nullable=False),
        Column("rating", Float, nullable=False),
        Column("badge_id", Integer, ForeignKey('badges.id')),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )
    op.create_table(
        'logout',
        Column("id", Integer, primary_key=True, index=True),
        Column("token", String),
    )
    op.create_table(
        "documents",
        Column("id", Integer, primary_key=True, index=True),
        Column("name", String),
        Column("type", String),  # profile, verification, hotel
        Column("verified", Boolean, default=False),
        Column("url", String, nullable=False),
        Column("createdBy", Integer, ForeignKey("users.id")),
        Column("createdAt", DateTime, default=datetime.utcnow()),
        Column("updatedAt", DateTime, onupdate=datetime.utcnow()),
    )


def downgrade():
    op.drop_table("countries")
    op.drop_table("users")
    op.drop_table("bank_informations")
    op.drop_table("badges")
    op.drop_table("contractors")
    op.drop_table("hotels")
    op.drop_table("hotel_admins")
    op.drop_table("admins")
    op.drop_table("shifts")
    op.drop_table("shift_cancellations")
    op.drop_table("billings")
    op.drop_table("notifications")
    op.drop_table("job_roles")
    op.drop_table("certificates")
    op.drop_table("reviews")
    op.drop_table("logout")
    op.drop_table("documents")


















