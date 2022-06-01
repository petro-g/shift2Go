from datetime import datetime

from sqlalchemy.sql.elements import False_

from app.config import constants
from app.db.session import Base
from sqlalchemy import (ARRAY, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, JSON, Time, and_)
from sqlalchemy.orm import relationship


class Country(Base):
    __tablename__ = 'countries'

    code = Column(String(2), primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    email = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    countryCode = Column(String, ForeignKey('countries.code'))
    phone = Column(String, nullable=True)
    latitude = Column(Float)
    longitude = Column(Float)
    userType = Column(String, nullable=False)
    address = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    deviceTokens = Column(ARRAY(String))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    admin = relationship('Admins', backref='owner', uselist=False)
    manager = relationship('HotelAdmins', backref='owner', uselist=False)
    contractor = relationship('Contractors', backref='owner', uselist=False)
    certificate = relationship('Certificates', backref='owner', uselist=False)
    jobrole = relationship('JobRoles', backref='owner', uselist=False)
    cancelled_shifts = relationship(
        'ShiftCancellations', backref='owner', uselist=True)


class BankInformations(Base):
    __tablename__ = "bank_informations"

    id = Column(Integer, primary_key=True, index=True)
    createdBy = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    accountNumber = Column(String, nullable=False)
    routingNumber = Column(String, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    owner = relationship('User', backref='bank')


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    createdBy = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    image = Column(String, nullable=True)
    type = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())


class Contractors(Base):
    __tablename__ = 'contractors'

    id = Column(Integer, primary_key=True, index=True)
    userID = Column(Integer, ForeignKey('users.id'), nullable=False)
    profilePicture = Column(String)
    rating = Column(Float)
    bank_id = Column(Integer, ForeignKey('bank_informations.id'))
    completedShiftsCount = Column(Integer)
    verified = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    jobRoles = Column(ARRAY(Integer))
    certificate_ids = Column(ARRAY(Integer))
    badge_count = Column(Integer, nullable=True, default=0)
    bank = relationship('BankInformations', backref='contractor',
                        primaryjoin="remote(BankInformations.createdBy) == foreign(Contractors.userID)")
    reviews = relationship(
        'Reviews', primaryjoin="remote(Reviews.reviewee_id) == foreign(Contractors.userID)", uselist=True)
    roles = relationship(
        'JobRoles', primaryjoin="remote(JobRoles.id) == foreign(any_(Contractors.jobRoles))", uselist=True)
    certificates = relationship(
        'Certificates', primaryjoin="remote(Certificates.createdBy) == foreign(Contractors.userID)", uselist=True)
    documents = relationship(
        'Documents', primaryjoin="remote(Documents.createdBy) == foreign(Contractors.userID)", uselist=True)
    notification = relationship(
        'NotificationSettings', primaryjoin="remote(NotificationSettings.createdBy) == foreign(Contractors.userID)", uselist=True)


class Hotels(Base):
    __tablename__ = 'hotels'

    id = Column(Integer, primary_key=True, index=True)
    createdBy = Column(Integer, ForeignKey('users.id'), nullable=False)
    hotelAdmin = Column(Integer, ForeignKey('hotel_admins.id'), nullable=False)
    name = Column(String, nullable=False)
    address = Column(String)
    phone = Column(String, nullable=False)
    employerIdentificationNumber = Column(String)
    bank_id = Column(Integer, ForeignKey('bank_informations.id'))
    pictures = Column(ARRAY(String))
    favouriteContractors = Column(ARRAY(Integer))
    contractorsRadius = Column(Float, default=20)
    latitude = Column(Float, nullable=False, default=0.0)
    longitude = Column(Float, nullable=False, default=0.0)
    notification = Column(JSON, default={
        'email': True,
        'push': True
    })
    rating = Column(Float)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    bank = relationship('BankInformations')
    reviews = relationship(
        'Reviews', primaryjoin="remote(Reviews.reviewee_id) == foreign(Hotels.id)", uselist=True)
    favourites = relationship(
        'Contractors', primaryjoin="remote(Contractors.id) == foreign(any_(Hotels.favouriteContractors))", uselist=True)


class HotelAdmins(Base):
    __tablename__ = 'hotel_admins'

    id = Column(Integer, primary_key=True, index=True)
    userID = Column(Integer, ForeignKey('users.id'), nullable=False)
    profilePicture = Column(String)
    rating = Column(Float)
    verified = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    hotels = relationship('Hotels', backref='manager', uselist=True)
    notification = relationship(
        'NotificationSettings', primaryjoin="remote(NotificationSettings.createdBy) == foreign(HotelAdmins.userID)", uselist=False)


class Admins(Base):
    __tablename__ = 'admins'

    id = Column(Integer, primary_key=True, index=True)
    userID = Column(Integer, ForeignKey('users.id'), nullable=False)
    profilePicture = Column(String)
    rating = Column(Float)
    verified = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())


class Shifts(Base):
    __tablename__ = 'shifts'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    hotel_id = Column(Integer, ForeignKey('hotels.id'), nullable=False)
    roles_ids = Column(ARRAY(Integer))
    pay = Column(Float, nullable=False)
    startTime = Column(DateTime, nullable=False)
    endTime = Column(DateTime, nullable=False)
    startedAt = Column(DateTime)
    endedAt = Column(DateTime)
    instructions = Column(String)
    requiredCertificatesTypes = Column(ARRAY(Integer))
    targetAudience = Column(ARRAY(Integer))
    audienceType = Column(String, default=constants.AUDIENCE_TYPE_MARKET)
    clockInLatitude = Column(Float)
    clockOutLatitude = Column(Float)
    clockInLongitude = Column(Float)
    clockOutLongitude = Column(Float)
    status = Column(String, default=constants.SHIFT_PENDING)
    active = Column(Boolean, default=True)
    contractor_id = Column(Integer, ForeignKey('contractors.id'))
    confirmed = Column(Boolean, default=False)
    createdBy = Column(Integer, ForeignKey('users.id'))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    contractor = relationship('Contractors')
    requests = relationship('ShiftRequests', uselist=True)
    hotel = relationship('Hotels')
    manager = relationship(
        'HotelAdmins', primaryjoin="remote(HotelAdmins.userID) == foreign(Shifts.createdBy)")
    roles = relationship(
        'JobRoles', primaryjoin="remote(JobRoles.id) == foreign(any_(Shifts.roles_ids))", uselist=True)
    certificates_types = relationship(
        'CertificateTypes', primaryjoin="remote(CertificateTypes.id) == foreign(any_(Shifts.requiredCertificatesTypes))", uselist=True)
    owner = relationship('User')


class ShiftCancellations(Base):
    __tablename__ = 'shift_cancellations'

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'))
    reason = Column(String, nullable=True)
    cancelledBy = Column(Integer, ForeignKey('users.id'))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    shift = relationship('Shifts', uselist=False)


class Billings(Base):
    __tablename__ = 'billings'

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'))
    hotel_id = Column(Integer, ForeignKey('hotels.id'))
    status = Column(String, default=constants.BILLING_PENDING)
    createdBy = Column(Integer, ForeignKey('users.id'))
    paymentTransactionID = Column(String)
    amountPayableToShift2go = Column(Float)
    amountPayableToContractor = Column(Float)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    shift = relationship('Shifts')
    hotel = relationship('Hotels')
    owner = relationship('User')


class Notifications(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    message = Column(String)
    notificationType = Column(String, default=constants.NOTIFICATION_BOTH)
    receivers = Column(ARRAY(Integer))
    createdBy = Column(Integer, ForeignKey('users.id'))
    readBy = Column(ARRAY(Integer))
    failed = Column(ARRAY(Integer))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    sender = relationship('User')


class JobRoles(Base):
    __tablename__ = 'job_roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    image = Column(String, nullable=False)
    createdBy = Column(Integer, ForeignKey('users.id'))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())


class Certificates(Base):
    __tablename__ = 'certificates'

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    certificate_type_id = Column(Integer, ForeignKey('certificate_types.id'))
    createdBy = Column(Integer, ForeignKey('users.id'))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    type = relationship('CertificateTypes', uselist=False)


class Reviews(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'))
    reviewee_id = Column(Integer)  # HOTEL_ID or USER_ID
    reviewee_type = Column(String)  # HOTEL or USER
    reviewer = Column(Integer, ForeignKey('users.id'))
    comment = Column(String, nullable=False)
    rating = Column(Float, nullable=False)
    badge_id = Column(Integer, ForeignKey('badges.id'))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    shift = relationship('Shifts', backref='reviews')
    owner = relationship('User')
    badge = relationship('Badge')


class BlackListedTokens(Base):
    __tablename__ = 'logout'
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String)


class Documents(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    verified = Column(Boolean, default=False)
    url = Column(String, nullable=False)
    createdBy = Column(Integer, ForeignKey("users.id"))
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    owner = relationship('User')


class ShiftRequests(Base):
    __tablename__ = "shift_request"

    id = Column(Integer, primary_key=True, index=True)
    notes = Column(String)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False)
    createdBy = Column(Integer, ForeignKey('users.id'), nullable=False)
    accepted = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    shift = relationship('Shifts')
    owner = relationship('User')
    contractor = relationship(
        'Contractors', primaryjoin="remote(Contractors.userID) == foreign(ShiftRequests.createdBy)")


class NotificationSettings(Base):
    __tablename__ = 'notification_settings'

    id = Column(Integer, primary_key=True, index=True)
    push = Column(Boolean, default=True)
    email = Column(Boolean, default=True)
    reminder = Column(Integer, default=1)
    cancels_shift = Column(Boolean, default=True)
    ends_shift = Column(Boolean, default=True)
    begins_shift = Column(Boolean, default=True)
    accepts_shift = Column(Boolean, default=True)
    declines_shift = Column(Boolean, default=True)
    createdBy = Column(Integer, ForeignKey('users.id'), nullable=False)
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
    owner = relationship('User')


class CertificateTypes(Base):
    __tablename__ = 'certificate_types'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    createdAt = Column(DateTime, default=datetime.utcnow())
    updatedAt = Column(DateTime, onupdate=datetime.utcnow())
