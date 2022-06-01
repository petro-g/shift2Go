import typing as t
from datetime import datetime, timedelta, date
import pytz

from app.config import constants
from app.config.config import PAGE_LIMIT, SHIFT2GO_PERCENTAGE, SQLALCHEMY_DATABASE_URI
from app.config.security import get_password_hash
from app.db.session import Base, engine, get_db
from app.celery_config.tasks import notification, email
from app.celery_config.tasks.utils import (send_manager_notification,
                                           shift_clock_in_logic, shift_clock_out_logic)
from app.config.utils import (Pagination, check_found,
                              generate_accepted_shift_notification_message,
                              generate_awarded_shift_notification_message,
                              generate_decline_shift_notification_message,
                              generate_shift_clockout_notification_message,
                              generate_shift_completed_notification_message,
                              generate_shift_request_notification_message,
                              generate_upcoming_shift_notification_message)
from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import any_
from sqlalchemy_utils import database_exists, create_database, drop_database

from . import models, schemas

utc = pytz.UTC


def create_test_super_admin(db: Session) -> models.User:
    hashed_password = get_password_hash('password')
    db_user = models.User(
        firstname='Shift2Go',
        lastname='Admin',
        email='admin@shift2go.com',
        is_active=True,
        userType=constants.ADMIN,
        hashed_password=hashed_password,
        is_superuser=True,
        is_verified=True,
        phone='233504359666',
        address='Accra, Ghana'
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    db_admin = models.Admins(
        userID=db_user.id
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)

    return db_user


def user_is_logged_out(db: Session, token: str) -> bool:
    logout = db.query(models.BlackListedTokens).filter(
        models.BlackListedTokens.token == token).first()
    if logout:
        return True
    return False


def logout_user(db: Session, token: str):
    logout = db.query(models.BlackListedTokens).filter(
        models.BlackListedTokens.token == token).first()
    if logout:
        return
    logout = models.BlackListedTokens(token=token)
    db.add(logout)
    db.commit()
    db.refresh(logout)
    return


def get_user_by_email(db: Session, email: str) -> models.User:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def contractor_signup(db: Session, request: schemas.ContractorIn) -> models.Contractors:
    user = get_user_by_email(db, request.email)
    if user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Email address has been registered')
    if request.jobRoles is not None:
        for role in request.jobRoles:
            get_jobrole(db, role)

    hashed_password = get_password_hash(request.password)
    # create user
    db_user = models.User(
        firstname=request.firstname,
        lastname=request.lastname,
        email=request.email,
        phone=request.phone,
        address=request.address,
        userType=constants.CONTRACTOR,
        hashed_password=hashed_password,
        deviceTokens=request.deviceTokens,
        is_superuser=False,
        is_verified=True,
        latitude=request.latitude,
        longitude=request.longitude
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if request.bank is not None:
        # add bank information
        bank = models.BankInformations(
            name=request.bank.name,
            routingNumber=request.bank.routingNumber,
            accountNumber=request.bank.accountNumber,
            createdBy=db_user.id
        )
        db.add(bank)
        db.commit()
        db.refresh(bank)

    if request.jobRoles is not None:
        for id in request.jobRoles:
            get_jobrole(db, id)

    # create Contractor
    db_contractor = models.Contractors(
        userID=db_user.id,
        profilePicture=request.profilePicture,
        jobRoles=request.jobRoles,
    )
    db.add(db_contractor)
    db.commit()
    db.refresh(db_contractor)

    # create notification
    notification = models.NotificationSettings(
        email=True,
        push=True,
        createdBy=db_user.id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return db_contractor


def get_contractor(db, user: models.User) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.userID == user.id
    ).first()
    check_found(contractor, 'Contractor')
    return contractor


def get_contractor_by_user_id(db, id: int) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.userID == id
    ).first()
    check_found(contractor, 'Contractor')
    return contractor


def get_contractor_by_id(db, id: int) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.id == id
    ).first()
    check_found(contractor, 'Contractor')
    return contractor


def contractor_verify(db, contractor_id: int) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.verified == False,
        models.Contractors.id == contractor_id
    ).first()
    check_found(contractor, 'Contractor')
    contractor.verified = True
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    return contractor


def unverify_contractor(db, contractor_id: int) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.id == contractor_id
    ).first()
    check_found(contractor, 'Contractor')
    contractor.verified = False
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    return contractor


def delete_unverify_contractor(db: Session, contractor_id: int) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.id == contractor_id,
        models.Contractors.verified == False
    ).first()
    check_found(contractor, 'Contractor')
    user = get_user_by_id(db, contractor.userID)
    notification_setting = get_notification_setting(db, user)
    db.delete(notification_setting)
    db.delete(contractor)
    db.delete(user)
    db.commit()
    return contractor


def delete_contractor(db, contractor_id: int) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.id == contractor_id).first()
    check_found(contractor, 'Contractor')
    user = get_user_by_id(db, contractor.userID)
    notification_setting = get_notification_setting(db, user)
    db.delete(notification_setting)
    db.delete(contractor)
    db.delete(user)
    db.commit()
    return contractor


def update_contractor(db: Session, user: models.User, request: schemas.ContractorEdit,
                      contractor_id: int = None) -> models.Contractors:
    contractor: models.Contractors = get_contractor_by_id(
        db, contractor_id) if contractor_id is not None else get_contractor(db, user)
    # update user
    if contractor_id is not None:
        user = get_user_by_id(db, contractor.userID)
    if request.firstname is not None:
        user.firstname = request.firstname
    if request.lastname is not None:
        user.lastname = request.lastname
    if request.phone is not None:
        user.phone = request.phone
    if request.address is not None:
        user.address = request.address
    if request.latitude is not None:
        user.latitude = request.latitude
    if request.longitude is not None:
        user.longitude = request.longitude
    if request.deviceTokens is not None:
        if user.deviceTokens is None:
            user.deviceTokens = request.deviceTokens
        else:
            old_tokens = user.deviceTokens
            user.deviceTokens = None
            db.add(user)
            db.commit()
            db.refresh(user)
            new_tokens = []
            for item in request.deviceTokens:
                new_tokens.append(item)
            for item in old_tokens:
                if item not in new_tokens:
                    new_tokens.append(item)
            user.deviceTokens = new_tokens
    db.add(user)
    db.commit()
    db.refresh(user)

    if request.jobRoles is not None:
        if contractor.jobRoles is None:
            contractor.jobRoles = request.jobRoles
        else:
            for id in request.jobRoles:
                if id not in contractor.jobRoles:
                    get_jobrole(db, id)
                    contractor.jobRoles.append(id)

    if request.profilePicture is not None:
        contractor.profilePicture = request.profilePicture

    db.add(contractor)
    db.commit()
    db.refresh(contractor)

    return contractor


def create_admin(db: Session, request: schemas.AdminRegister) -> models.Admins:
    user = get_user_by_email(db, request.email)
    if user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Email address has been registered')
    hashed_password = get_password_hash(request.password)
    # create user
    db_user = models.User(
        firstname="",
        lastname="",
        email=request.email,
        phone="",
        address="",
        userType=constants.ADMIN,
        hashed_password=hashed_password,
        is_superuser=True,
        is_verified=True,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # create Admin
    db_admin = models.Admins(
        userID=db_user.id,
        # profilePicture=request.profilePicture
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)

    return db_admin


def get_admin_by_user_id(db, user: models.User) -> models.Admins:
    admin = db.query(models.Admins).filter(
        models.Admins.userID == user.id).first()
    check_found(admin, 'Admin')
    return admin


def get_country_by_code(db: Session, code: str):
    country = db.query(models.Country).filter(
        or_(models.Country.code == code, models.Country.name == code)
    ).first()
    check_found(country, 'Country')
    return country


def admin_update(db: Session, user: models.User, request: schemas.AdminEdit) -> models.Admins:
    admin = get_admin_by_user_id(db, user)
    if request.countryCode is not None:
        country = get_country_by_code(db, request.countryCode)
        user.countryCode = country.code
    # update user
    if request.firstname is not None:
        user.firstname = request.firstname
    if request.lastname is not None:
        user.lastname = request.lastname
    if request.phone is not None:
        user.phone = request.phone
    if request.address is not None:
        user.address = request.address
    if request.latitude is not None:
        user.latitude = request.latitude
    if request.longitude is not None:
        user.longitude = request.longitude
    if request.deviceTokens is not None:
        if user.deviceTokens is None:
            user.deviceTokens = request.deviceTokens
        else:
            for item in request.deviceTokens:
                if item not in user.deviceTokens:
                    user.deviceTokens.append(item)
    db.add(user)
    db.commit()
    db.refresh(user)

    if request.profilePicture is not None:
        admin.profilePicture = request.profilePicture
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


def get_users(db: Session, page: int = 1, ) -> Pagination:
    users = db.query(models.User).offset(
        (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    total = db.query(models.User).count()
    return Pagination(data=users, count=total)


def get_user(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_managers(db: Session, skip: int = 0, limit: int = 100) -> t.List[models.HotelAdmins]:
    return db.query(models.HotelAdmins).offset(skip).limit(limit).all()


def get_contractors(db: Session, page: int = 1) -> Pagination:
    contractors = db.query(models.Contractors).offset(
        (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Contractors).count()
    return Pagination(data=contractors, count=count)


def get_unverified_contractors(db: Session, page: int) -> Pagination:
    contractors = db.query(models.Contractors).filter(
        models.Contractors.verified == False
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Contractors).filter(
        models.Contractors.verified == False
    ).count()
    return Pagination(data=contractors, count=count)


def get_single_unverified_contractor(
        db: Session, contractor_id: int
) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.id == contractor_id,
        models.Contractors.verified == False
    ).first()
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contractor not found or unverified")
    return contractor


def get_single_verified_contractor(
        db: Session, contractor_id: int
) -> models.Contractors:
    contractor = db.query(models.Contractors).filter(
        models.Contractors.id == contractor_id,
        models.Contractors.verified == True
    ).first()
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Contractor id={contractor_id} not found or unverified")
    return contractor


def get_banks(db: Session, user: models.User, page) -> Pagination:
    if user.userType == constants.ADMIN:
        data = db.query(models.BankInformations).offset(
            (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.BankInformations).count()
        return Pagination(data=data, count=count)
    else:
        data = db.query(models.BankInformations).filter(
            models.BankInformations.createdBy == user.id
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = data = db.query(models.BankInformations).filter(
            models.BankInformations.createdBy == user.id
        ).count()
        return Pagination(data=data, count=count)


def get_bank_no_catch(db: Session, user: models.User) -> models.BankInformations:
    return db.query(models.BankInformations).filter(
        models.BankInformations.createdBy == user.id
    ).first()


def get_bank(db: Session, user: models.User, bank_id: int = None) -> models.BankInformations:
    if user.userType == constants.ADMIN:
        bank = db.query(models.BankInformations).filter(
            models.BankInformations.id == bank_id).first()
        if not bank:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Bank Information not found")
        return bank
    bank: models.BankInformations = None
    if bank_id is None:
        bank = db.query(models.BankInformations).filter(
            or_(models.BankInformations.createdBy == user.id,
                models.BankInformations.id == bank_id)
        ).first()
    else:
        bank = db.query(models.BankInformations).filter(
            and_(models.BankInformations.createdBy == user.id,
                 models.BankInformations.id == bank_id)
        ).first()

    if not bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bank Information not found")
    return bank


def create_bank(db: Session, user: models.User, request: schemas.BankIn) -> models.BankInformations:
    bank = models.BankInformations(
        name=request.name,
        accountNumber=request.accountNumber,
        routingNumber=request.routingNumber,
        createdBy=user.id
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    if user.userType == constants.CONTRACTOR:
        contractor = get_contractor(db, user)
        contractor.bank_id = bank.id
        db.add(contractor)
        db.commit()
    return bank


def edit_my_bank(db: Session, user: models.User, request: schemas.BankEdit) -> models.BankInformations:
    if request.name is None and request.accountNumber is None and request.routingNumber is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='All fields cannot be null')
    bank = db.query(models.BankInformations).filter(
        models.BankInformations.createdBy == user.id
    ).first()
    check_found(bank, 'Bank')
    if request.name is not None:
        bank.name = request.name
    if request.accountNumber is not None:
        bank.accountNumber = request.accountNumber
    if request.routingNumber is not None:
        bank.routingNumber = request.routingNumber

    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


def delete_bank(db: Session, user: models.User, bank_id: int) -> bool:
    if user.userType == constants.ADMIN:
        bank = db.query(models.BankInformations).filter(
            models.BankInformations.id == bank_id).first()
        check_found(bank, 'Bank Information')
        db.delete(bank)
        db.commit()
        return True

    bank = db.query(models.BankInformations).filter(
        models.BankInformations.createdBy == user.id,
        models.BankInformations.id == bank_id
    ).all()
    check_found(bank, 'Bank Information')
    db.delete(bank)
    db.commit()
    return True


def get_badges(db: Session, page: int) -> Pagination:
    badges = db.query(models.Badge).offset(
        (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Badge).count()
    return Pagination(data=badges, count=count)


def get_badge(db: Session, badge_id: int) -> models.Badge:
    badge = db.query(models.Badge).filter(
        models.Badge.id == badge_id).first()
    check_found(badge, 'Badge')
    return badge


def get_hotel_badges(db: Session, user: models.User, hotel_id: int) -> t.List[models.Badge]:
    hotel = None
    if user.userType == constants.MANAGER:
        hotel = get_hotel_by_id_and_user(db, user, hotel_id)
    else:
        hotel = get_hotel_by_id(db, hotel_id)
    badges = db.query(models.Badge).join(
        models.Reviews,
        models.Reviews.badge_id == models.Badge.id
    ).filter(
        models.Reviews.reviewee_id == hotel.id,
        models.Reviews.reviewee_type == constants.REVIWEE_TYPE_HOTEL
    ).all()
    return badges


def get_contractor_badges(db: Session, user: models.User, contractor_id: int) -> t.List[models.Badge]:
    contractor = None
    if user.userType == constants.CONTRACTOR:
        contractor = get_contractor_by_user_id(db, user.id)
        if contractor_id is not None:
            if not contractor.id == contractor_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail='Cannot view badges for a different contractor')
        contractor = get_single_verified_contractor(db, contractor.id)
    else:
        if contractor_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Please a contractor_id as a query parameter')
        contractor = get_single_verified_contractor(db, contractor_id)
    badges = db.query(models.Badge).join(
        models.Reviews,
        models.Reviews.badge_id == models.Badge.id
    ).filter(
        models.Reviews.reviewee_id == contractor.userID,
        models.Reviews.reviewee_type == constants.REVIWEE_TYPE_USER
    ).all()
    return badges


def create_badge(db: Session, user: models.User, request: schemas.BadgeIn) -> models.Badge:
    if request.type != constants.REVIWEE_TYPE_HOTEL and request.type != constants.REVIWEE_TYPE_USER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="'type' should be one of 'HOTEL' or 'USER'")
    badge = models.Badge(
        name=request.name,
        image=request.image,
        type=request.type,
        createdBy=user.id
    )
    db.add(badge)
    db.commit()
    db.refresh(badge)
    return badge


def delete_badge(db: Session, user: models.User, badge_id: int) -> bool:
    badge = db.query(models.Badge).filter(
        models.Badge.id == badge_id).first()
    check_found(badge, 'Badge')
    db.delete(badge)
    db.commit()
    return True


def get_hotel_admin_by_user_id(db: Session, user: models.User) -> models.HotelAdmins:
    hotel_admin = db.query(models.HotelAdmins).filter(
        models.HotelAdmins.userID == user.id
    ).first()
    if not hotel_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Hotel Admin not found')
    return hotel_admin


def get_bank_by_id(db: Session, bank_id: int) -> models.BankInformations:
    bank = db.query(models.BankInformations).filter(
        models.BankInformations.id == bank_id
    ).first()
    check_found(bank, 'Bank')
    return bank


def add_hotel(db: Session, user: models.User, request: schemas.HotelIn) -> models.Hotels:
    hotel_admin = get_hotel_admin_by_user_id(db, user)
    # get_bank_by_id(db, request.bank_id)
    bank = models.BankInformations(**request.bank.dict(), createdBy=user.id)
    db.add(bank)
    db.commit()
    db.refresh(bank)
    hotel = models.Hotels(
        name=request.legal_name,
        phone=request.phone,
        address=request.address,
        createdBy=user.id,
        hotelAdmin=hotel_admin.id,
        employerIdentificationNumber=request.employerIdentificationNumber,
        bank_id=bank.id,
        pictures=request.pictures,
        longitude=request.longitude,
        latitude=request.latitude,
        notification={
            'email': request.notification.email,
            'push': request.notification.push
        }
    )
    if request.contractorsRadius is not None:
        hotel.contractorsRadius = request.contractorsRadius,
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def get_hotels(db: Session, user: models.User) -> t.List[models.Hotels]:
    if user.userType == constants.ADMIN or user.userType == constants.CONTRACTOR:
        return db.query(models.Hotels).all()
    else:
        hotel_admin = get_hotel_admin_by_user_id(db, user)
        return db.query(models.Hotels).filter(
            models.Hotels.createdBy == user.id,
            models.Hotels.hotelAdmin == hotel_admin.id
        ).all()


def get_hotel(db: Session, user: models.User, hotel_id: int) -> models.Hotels:
    if user.userType == constants.ADMIN or user.userType == constants.CONTRACTOR:
        hotel = db.query(models.Hotels).filter(
            models.Hotels.id == hotel_id
        ).first()
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Hotel not found')
        return hotel
    else:
        hotel_admin = get_hotel_admin_by_user_id(db, user)
        hotel = db.query(models.Hotels).filter(
            models.Hotels.createdBy == user.id,
            models.Hotels.hotelAdmin == hotel_admin.id,
            models.Hotels.id == hotel_id
        ).first()
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Hotel not found')
        return hotel


def get_hotel_by_id_and_user(db: Session, user: models.User, hotel_id: int) -> models.Hotels:
    if user.userType == constants.MANAGER:
        hotel_admin = get_hotel_admin_by_user_id(db, user)
        hotel = db.query(models.Hotels).filter(
            models.Hotels.createdBy == user.id,
            models.Hotels.hotelAdmin == hotel_admin.id,
            models.Hotels.id == hotel_id
        ).first()
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Hotel not found')
        return hotel
    else:
        hotel = db.query(models.Hotels).filter(
            models.Hotels.id == hotel_id
        ).first()
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Hotel not found')
        return hotel


def add_hotel_favourite_contractor(db: Session, user: models.User, contractor_id: int, hotel_id: int) -> models.Hotels:
    contractor = get_single_verified_contractor(db, contractor_id)
    hotel = get_hotel_by_id_and_user(db, user, hotel_id)
    if hotel.favouriteContractors is None:
        hotel.favouriteContractors = []
    if contractor.id not in hotel.favouriteContractors:
        old_ids = hotel.favouriteContractors
        hotel.favouriteContractors = None
        db.add(hotel)
        db.commit()
        db.refresh(hotel)
        new_ids = []
        for item in old_ids:
            new_ids.append(item)
        new_ids.append(contractor.id)
        hotel.favouriteContractors = new_ids
    else:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                            detail='Contractor is already a favourite')

    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def remove_hotel_favourite_contractor(db: Session, user: models.User, contractor_id: int,
                                      hotel_id: int) -> models.Hotels:
    contractor = get_single_verified_contractor(db, contractor_id)
    hotel = get_hotel_by_id_and_user(db, user, hotel_id)
    not_favourite_exception = HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Contractor is not a favourite')
    if hotel.favouriteContractors is None:
        raise not_favourite_exception
    if contractor.id in hotel.favouriteContractors:
        old_ids = hotel.favouriteContractors
        hotel.favouriteContractors = None
        db.add(hotel)
        db.commit()
        db.refresh(hotel)
        new_ids = []
        for item in old_ids:
            new_ids.append(item)
        new_ids.remove(contractor.id)
        hotel.favouriteContractors = new_ids
    else:
        raise not_favourite_exception
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def get_favourite_contractors(db: Session, user: models.User, page: int, hotel_id: int, job_role_id: int) -> Pagination:
    hotel = get_hotel_by_id_and_user(db, user, hotel_id)
    if job_role_id is not None:
        get_jobrole(db, job_role_id)
        contractors = db.query(models.Contractors).filter(
            models.Contractors.id == any_(hotel.favouriteContractors),
            job_role_id == any_(models.Contractors.jobRoles)
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()

        count = db.query(models.Contractors).filter(
            models.Contractors.id == any_(hotel.favouriteContractors),
            job_role_id == any_(models.Contractors.jobRoles)
        ).count()
        return Pagination(data=contractors, count=count)
    else:
        contractors = db.query(models.Contractors).filter(
            models.Contractors.id == any_(hotel.favouriteContractors)
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.Contractors).filter(
            models.Contractors.id == any_(hotel.favouriteContractors)
        ).count()
        return Pagination(data=contractors, count=count)


def edit_hotel(db: Session, user: models.User, request: schemas.HotelEdit, hotel_id: int) -> models.Hotels:
    hotel = get_hotel_by_id_and_user(db, user, hotel_id)

    if request.address is not None:
        hotel.address = request.address
    if request.name is not None:
        hotel.name = request.name
    if request.phone is not None:
        hotel.phone = request.phone
    if request.employerIdentificationNumber is not None:
        hotel.employerIdentificationNumber = request.employerIdentificationNumber
    if request.contractorsRadius is not None:
        hotel.contractorsRadius = request.contractorsRadius
    if request.latitude is not None:
        hotel.latitude = request.latitude
    if request.longitude is not None:
        hotel.longitude = request.longitude
    if request.pictures is not None:
        if hotel.pictures is None:
            hotel.pictures = request.pictures
        else:
            for id in request.pictures:
                if id not in hotel.pictures:
                    hotel.pictures.append(id)
    if request.notification:
        hotel.notification = request.notification.dict()

    if request.bank:
        bank = get_bank_by_id(db, hotel.bank_id)
        if request.bank.name is not None:
            bank.name = request.bank.name
        if request.bank.accountNumber is not None:
            bank.accountNumber = request.bank.accountNumber
        if request.bank.routingNumber is not None:
            bank.routingNumber = request.bank.routingNumber
        db.add(bank)
        db.commit()
        db.refresh(bank)

    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return hotel


def delete_hotel(db: Session, user: models.User, hotel_id: int) -> bool:
    hotel = get_hotel_by_id_and_user(db, user, hotel_id)

    db.delete(hotel)
    db.commit()
    return True


def register_manager(db: Session, request: schemas.HotelAdminRegister) -> models.HotelAdmins:
    user = get_user_by_email(db, request.email)
    if user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Email address has been registered')
    hashed_password = get_password_hash(request.password)
    # create user
    db_user = models.User(
        firstname=request.firstname,
        lastname=request.lastname,
        email=request.email,
        phone=request.phone,
        address=request.address,
        userType=constants.MANAGER,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # create Manager
    db_admin = models.HotelAdmins(
        userID=db_user.id,
        profilePicture=request.profilePicture
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)

    # create notification
    notification = models.NotificationSettings(
        email=True,
        push=True,
        createdBy=db_user.id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return db_admin


def get_managers(db: Session, page: int) -> Pagination:
    managers = db.query(models.HotelAdmins).offset(
        (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.HotelAdmins).count()
    return Pagination(data=managers, count=count)


def get_manager_by_user_id(db: Session, user_id: int) -> models.HotelAdmins:
    manager = db.query(models.HotelAdmins).filter(
        models.HotelAdmins.userID == user_id
    ).first()
    check_found(manager, 'Hotel Manager')
    return manager


def get_manager_by_id(db: Session, manager_id: int) -> models.HotelAdmins:
    manager = db.query(models.HotelAdmins).filter(
        models.HotelAdmins.id == manager_id
    ).first()
    check_found(manager, 'Hotel Manager')
    return manager


def delete_manager(db: Session, manager_id: int) -> bool:
    manager = get_manager_by_id(db, manager_id)
    db.delete(manager)
    db.commit()
    return True


def add_certificate(db: Session, user: models.User, request: schemas.CertificateIn) -> models.Certificates:
    # check if certificate type exist for user and update
    db_certificate = db.query(models.Certificates).filter(
        models.Certificates.certificate_type_id == request.certificate_type_id,
        models.Certificates.createdBy == user.id
    ).first()
    if db_certificate is not None:
        db_certificate.url = request.url
    else:
        db_certificate = models.Certificates(
            url=request.url,
            certificate_type_id=request.certificate_type_id,
            createdBy=user.id
        )
    db.add(db_certificate)
    db.commit()
    db.refresh(db_certificate)
    return db_certificate


def edit_certificate(db: Session, user: models.User, request: schemas.CertificateEdit,
                     certificate_id: int) -> models.Certificates:
    db_certificate = get_certificate(db, user, certificate_id)
    db_certificate.url = request.url
    db.add(db_certificate)
    db.commit()
    db.refresh(db_certificate)
    return db_certificate


def delete_certificate(db: Session, user: models.User, certificate_id: int) -> bool:
    db_certificate = get_certificate(db, user, certificate_id)
    db.delete(db_certificate)
    db.commit()
    return True


def get_certificate(db: Session, user: models.User, certificate_id: int) -> models.Certificates:
    if user.userType == constants.CONTRACTOR:
        certificate = db.query(models.Certificates).filter(
            models.Certificates.id == certificate_id,
            models.Certificates.createdBy == user.id
        ).first()
        check_found(certificate, f'Certificate with id={certificate_id}')
        return certificate

    certificate = db.query(models.Certificates).filter(
        models.Certificates.id == certificate_id,
    ).first()
    check_found(certificate, f'Certificate with id={certificate_id}')
    return certificate


def get_certificates_by_contractor_id(db: Session, contractor_id: int, page: int) -> Pagination:
    contractor = get_single_verified_contractor(db, contractor_id)
    certificates = db.query(models.Certificates).filter(
        models.Certificates.createdBy == contractor.userID
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Certificates).filter(
        models.Certificates.createdBy == contractor.userID
    ).count()
    return Pagination(data=certificates, count=count)


def get_system_certificates(db: Session, page: int) -> Pagination:
    certificates = db.query(models.Certificates).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Certificates).count()
    return Pagination(data=certificates, count=count)


def get_certificates(db: Session, user: models.User, page: int, contractor_id: t.Optional[int] = None) -> Pagination:
    if user.userType == constants.CONTRACTOR:
        certificates = db.query(models.Certificates).filter(
            models.Certificates.createdBy == user.id
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.Certificates).filter(
            models.Certificates.createdBy == user.id
        ).count()
        return Pagination(data=certificates, count=count)
    elif user.userType == constants.MANAGER:
        if contractor_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Manger needs to pass contractor id')
        return get_certificates_by_contractor_id(db, contractor_id, page)
    else:
        if contractor_id is not None:
            return get_certificates_by_contractor_id(db, contractor_id, page)
        certificates = db.query(models.Certificates).offset(
            (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.Certificates).count()
        return Pagination(data=certificates, count=count)


def add_jobrole(db: Session, user: models.User, request: schemas.JobRolesIn) -> models.JobRoles:
    db_jobrole = models.JobRoles(
        name=request.name,
        image=request.image,
        createdBy=user.id
    )
    db.add(db_jobrole)
    db.commit()
    db.refresh(db_jobrole)
    return db_jobrole


def edit_jobrole(db: Session, request: schemas.JobRolesEdit, jobrole_id: int) -> models.JobRoles:
    db_jobrole = get_jobrole(db, jobrole_id)
    db_jobrole.name = request.name
    if request.image is not None:
        db_jobrole.image = request.image
    db.add(db_jobrole)
    db.commit()
    db.refresh(db_jobrole)
    return db_jobrole


def delete_jobrole(db: Session, jobrole_id: int) -> bool:
    db_jobrole = get_jobrole(db, jobrole_id)
    db.delete(db_jobrole)
    db.commit()
    return True


def get_jobrole(db: Session, jobrole_id) -> models.JobRoles:
    jobrole = db.query(models.JobRoles).filter(
        models.JobRoles.id == jobrole_id
    ).first()
    check_found(jobrole, f'JobRole with id={jobrole_id}')
    return jobrole


def get_jobroles(db: Session) -> t.List[models.JobRoles]:
    db_jobroles = db.query(models.JobRoles).all()
    return db_jobroles


def get_shift_by_id(db: Session, shift_id: int) -> models.Shifts:
    shift = db.query(models.Shifts).filter(
        models.Shifts.id == shift_id).first()
    check_found(shift, 'Shift')
    return shift


def add_review(db: Session, user: models.User, request: schemas.ReviewsIn) -> models.Reviews:
    shift = get_shift_by_id(db, request.shift_id)
    if request.reviewee_type != constants.REVIWEE_TYPE_HOTEL and request.reviewee_type != constants.REVIWEE_TYPE_USER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="'reviewee_type' should be one of 'HOTEL' or 'USER'")
    if user.userType == constants.MANAGER:
        if not shift.createdBy == user.id or not shift.status == constants.SHIFT_COMPLETED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Manager cannot review on a shift they do not own or has not been completed")

    reviewee = None
    if request.reviewee_type == constants.REVIWEE_TYPE_HOTEL:
        if user.userType == constants.MANAGER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Hotel Manager cannot review a hotel")

        reviewee = get_hotel(db, user, shift.hotel_id)
    else:
        if user.userType == constants.CONTRACTOR:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Contractor cannot review a another Contractor")
        contractor = get_single_verified_contractor(db, shift.contractor_id)
        reviewee = get_user_by_id(db, contractor.userID)

    # check if contractor worked on shift
    if user.userType == constants.CONTRACTOR:
        contractor = get_contractor(db, user)
        if not shift.contractor_id == contractor.id or not shift.status == constants.SHIFT_COMPLETED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Contractor not allowed to review a shift they have not been awarded or have not completed')

    # check if manager worked on shift
    else:
        # manager = get_manager_by_user_id(db, user.id)
        if not shift.createdBy == user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail='Not allowed to review on shift you do not own')

    badge_id = None
    if request.badge_id is not None:
        badge = get_badge(db, request.badge_id)
        if badge.type is not None:
            if not badge.type == request.reviewee_type:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Cannot use a badge of 'type' {badge.type} for review type {request.reviewee_type}")

        badge_id = badge.id

    # check if user has already reviews for this shift
    old_review = db.query(models.Reviews).filter(
        models.Reviews.shift_id == shift.id,
        models.Reviews.reviewer == user.id
    ).first()
    if old_review:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='You cannot add another review for this shift. You can only edit or delete review for a shift')

    review = models.Reviews(
        shift_id=shift.id,
        badge_id=badge_id,
        reviewee_id=reviewee.id,
        reviewee_type=request.reviewee_type,
        reviewer=user.id,
        comment=request.comment,
        rating=request.rating
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_hotel_by_id(db: Session, hotel_id: int) -> models.Hotels:
    hotel = db.query(models.Hotels).filter(
        models.Hotels.id == hotel_id).first()
    check_found(hotel, 'Hotel')
    return hotel


def get_hotel_reviews(db: Session, hotel_id: int, page: int) -> Pagination:
    get_hotel_by_id(db, hotel_id)
    reviews = db.query(models.Reviews).filter(
        models.Reviews.reviewee_type == constants.REVIWEE_TYPE_HOTEL,
        models.Reviews.reviewee_id == hotel_id
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Reviews).filter(
        models.Reviews.reviewee_type == constants.REVIWEE_TYPE_HOTEL,
        models.Reviews.reviewee_id == hotel_id
    ).count()
    return Pagination(data=reviews, count=count)


def get_user_reviews(db: Session, user_id: int, page: int) -> Pagination:
    reviews = db.query(models.Reviews).filter(
        models.Reviews.reviewee_type == constants.REVIWEE_TYPE_USER,
        models.Reviews.reviewee_id == user_id
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Reviews).filter(
        models.Reviews.reviewee_type == constants.REVIWEE_TYPE_USER,
        models.Reviews.reviewee_id == user_id
    ).count()
    return Pagination(data=reviews, count=count)


def get_all_given_reviews(db: Session, user_id: int, page: int) -> Pagination:
    reviews = db.query(models.Reviews).filter(
        models.Reviews.reviewer == user_id
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Reviews).filter(
        models.Reviews.reviewer == user_id
    ).count()
    return Pagination(data=reviews, count=count)


def get_review(db: Session, review_id: int) -> models.Reviews:
    review = db.query(models.Reviews).filter(
        models.Reviews.id == review_id
    ).first()
    check_found(review, 'Review')
    return review


def edit_review(db: Session, user: models.User, request: schemas.ReviewsEdit, review_id: int) -> models.Reviews:
    review = get_review(db, review_id)
    if not user.userType == constants.ADMIN:
        if not review.reviewer == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Not allowed to edit review you do not own')

    if request.comment is not None:
        review.comment = request.comment
    if request.rating is not None:
        review.rating = request.rating

    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, user: models.User, review_id: int) -> bool:
    review = get_review(db, review_id)
    if not user.userType == constants.ADMIN:
        if not review.reviewer == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Not allowed to edit review you do not own')

    db.delete(review)
    db.commit()
    return True


def add_shift(db: Session, user: models.User, request: schemas.ShiftIn) -> models.Shifts:
    if request.audienceType != constants.AUDIENCE_TYPE_MARKET and request.audienceType != constants.AUDIENCE_TYPE_MANUAL and request.audienceType != constants.AUDIENCE_TYPE_FAVOURITE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='audienceType should be one of MARKET, MANUAL, FAVOURITE'
        )

    # check if ids exist
    hotel = get_hotel(db, user, request.hotel_id)
    for role_id in request.roles_ids:
        get_jobrole(db, role_id)
    if request.requiredCertificates is not None:
        for certificate_type in request.requiredCertificates:
            get_a_certificate_type(db, certificate_type)
    if request.targetAudience is not None:
        if request.audienceType == constants.AUDIENCE_TYPE_MARKET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Audience type MARKET should not have targetAudience'
            )
        if request.audienceType == constants.AUDIENCE_TYPE_MANUAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Audience type MANUAL should not have targetAudience'
            )
        for id in request.targetAudience:
            if id not in hotel.favouriteContractors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'targetAudience id {id} is not a favourite of hotel {hotel.name}'
                )
            get_single_verified_contractor(db, id)
    else:
        if request.audienceType == constants.AUDIENCE_TYPE_FAVOURITE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Only Audience type FAVOURITE should have targetAudience'
            )

    if request.contractor_id is not None:
        if request.audienceType == constants.AUDIENCE_TYPE_MARKET or request.audienceType == constants.AUDIENCE_TYPE_FAVOURITE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Only Audience type MANUAL should have contractor_id'
            )

    shift = models.Shifts(
        name=request.name,
        hotel_id=request.hotel_id,
        roles_ids=request.roles_ids,
        pay=request.pay,
        startTime=request.startTime,
        endTime=request.endTime,
        instructions=request.instructions,
        requiredCertificatesTypes=request.requiredCertificates,
        targetAudience=request.targetAudience,
        audienceType=request.audienceType,
        createdBy=user.id,
        contractor_id=request.contractor_id
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    shift_clock_in_logic.apply_async(kwargs={
        'shift_id': shift.id
    }, eta=shift.startTime + timedelta(minutes=15))

    shift_clock_out_logic.apply_async(kwargs={
        'shift_id': shift.id
    }, eta=shift.endTime + timedelta(minutes=15))

    return shift


def all_awarded_shifts(db: Session, user: models.User, page: int) -> Pagination:
    contractor = get_contractor(db, user)
    shifts = db.query(models.Shifts).filter(
        models.Shifts.active == True,
        models.Shifts.contractor_id == contractor.id,
        models.Shifts.status == constants.SHIFT_PENDING,
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()

    counter = db.query(models.Shifts).filter(
        models.Shifts.active == True,
        models.Shifts.contractor_id == contractor.id,
        models.Shifts.status == constants.SHIFT_PENDING,
    ).count()
    return Pagination(data=shifts, count=counter)


def get_shifts(db: Session, user: models.User, page: int, audience: str = None, role_id: int = None,
               date: date = None) -> Pagination:
    # discuss how contractor radius would be passed to api
    shifts = None

    if role_id is not None:
        get_jobrole(db, role_id)

    if audience is not None and audience != constants.AUDIENCE_TYPE_MANUAL and audience != constants.AUDIENCE_TYPE_MARKET and audience != constants.AUDIENCE_TYPE_FAVOURITE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='audience_type should be one of MARKET, FAVOURITE, MANUAL')

    if user.userType == constants.CONTRACTOR:
        contractor = get_contractor(db, user)
        if audience == constants.AUDIENCE_TYPE_MANUAL:
            shifts = db.query(models.Shifts).join(
                models.Hotels,
                models.Hotels.id == models.Shifts.hotel_id,
            ).filter(
                models.Shifts.contractor_id == contractor.id,
                models.Shifts.status == constants.SHIFT_PENDING,
                models.Shifts.active == True,
                models.Shifts.audienceType == constants.AUDIENCE_TYPE_MANUAL
            )
            # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            #                     detail='Contractors cannot see shift of type MANUAL')

        elif audience == constants.AUDIENCE_TYPE_FAVOURITE:
            shifts = db.query(models.Shifts).join(
                models.Hotels,
                models.Hotels.id == models.Shifts.hotel_id,
            ).filter(
                contractor.id == any_(models.Hotels.favouriteContractors),
                models.Shifts.active == True,
                models.Shifts.status == constants.SHIFT_PENDING,
                models.Shifts.audienceType == constants.AUDIENCE_TYPE_FAVOURITE
            )

        elif audience == constants.AUDIENCE_TYPE_MARKET:
            shifts = db.query(models.Shifts).filter(
                models.Shifts.active == True,
                models.Shifts.audienceType == constants.AUDIENCE_TYPE_MARKET,
                models.Shifts.status == constants.SHIFT_PENDING,
            )
        else:
            shifts = db.query(models.Shifts).join(
                models.Hotels,
                models.Hotels.id == models.Shifts.hotel_id
            ).filter(
                models.Shifts.status == constants.SHIFT_PENDING,
                models.Shifts.active == True,
                or_(
                    (
                            models.Shifts.status == constants.SHIFT_PENDING and
                            models.Shifts.audienceType == constants.AUDIENCE_TYPE_MARKET
                    ),
                    (
                            contractor.id == any_(models.Hotels.favouriteContractors) and
                            models.Shifts.status == constants.SHIFT_PENDING and
                            models.Shifts.audienceType == constants.AUDIENCE_TYPE_FAVOURITE
                    )
                )
            )
    elif user.userType == constants.MANAGER:
        shifts = db.query(models.Shifts).filter(
            models.Shifts.active == True,
            models.Shifts.createdBy == user.id
        )
        if audience is not None:
            shifts = shifts.filter(
                models.Shifts.active == True,
                models.Shifts.audienceType == audience
            )
    else:
        shifts = db.query(models.Shifts)
        if audience is not None:
            shifts = shifts.filter(
                models.Shifts.active == True,
                models.Shifts.audienceType == audience
            )

    if role_id is not None:
        shifts = shifts.filter(
            models.Shifts.active == True,
            role_id == any_(models.Shifts.roles_ids)
        )

    if date is not None:
        total = [item for item in shifts.all() if item.createdAt.date() == date]
        part = total[(page - 1) * PAGE_LIMIT:]
        final = part[:PAGE_LIMIT]
        return Pagination(
            data=final,
            count=len(total)
        )

    else:
        return Pagination(
            data=shifts.offset(
                (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all(),
            count=shifts.count()
        )


def get_hotel_shifts(db: Session, user: models.User, hotel_id: int, page: int, audience: str = None,
                     role_id: int = None, date: date = None) -> Pagination:
    # discuss how contractor radius would be passed to api
    hotel = get_hotel(db, user, hotel_id)
    shifts = None

    if role_id is not None:
        get_jobrole(db, role_id)

    if audience is not None and audience != constants.AUDIENCE_TYPE_MANUAL and audience != constants.AUDIENCE_TYPE_MARKET and audience != constants.AUDIENCE_TYPE_FAVOURITE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='audience_type should be one of MARKET, FAVOURITE, MANUAL')

    if user.userType == constants.CONTRACTOR:
        contractor = get_contractor(db, user)
        if audience == constants.AUDIENCE_TYPE_MANUAL:
            shifts = db.query(models.Shifts).join(
                models.Hotels,
                models.Hotels.id == models.Shifts.hotel_id,
            ).filter(
                models.Shifts.contractor_id == contractor.id,
                models.Shifts.status == constants.SHIFT_PENDING,
                models.Shifts.active == True,
                models.Shifts.audienceType == constants.AUDIENCE_TYPE_MANUAL,
                models.Shifts.hotel_id == hotel.id,
            )
            # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            #                     detail='Contractors cannot see shift of type MANUAL')

        elif audience == constants.AUDIENCE_TYPE_FAVOURITE:
            shifts = db.query(models.Shifts).join(
                models.Hotels,
                models.Hotels.id == models.Shifts.hotel_id,
            ).filter(
                contractor.id == any_(models.Hotels.favouriteContractors),
                models.Shifts.active == True,
                models.Shifts.status == constants.SHIFT_PENDING,
                models.Shifts.hotel_id == hotel.id,
                models.Shifts.audienceType == constants.AUDIENCE_TYPE_FAVOURITE
            )

        elif audience == constants.AUDIENCE_TYPE_MARKET:
            shifts = db.query(models.Shifts).filter(
                models.Shifts.active == True,
                models.Shifts.hotel_id == hotel.id,
                models.Shifts.audienceType == constants.AUDIENCE_TYPE_MARKET,
                models.Shifts.status == constants.SHIFT_PENDING,
            )
        else:
            print('boooooom')
            shifts = db.query(models.Shifts).join(
                models.Hotels,
                models.Hotels.id == models.Shifts.hotel_id
            ).filter(
                models.Shifts.hotel_id == hotel.id,
                models.Shifts.status == constants.SHIFT_PENDING,
                models.Shifts.active == True,
                or_(
                    (
                            models.Shifts.status == constants.SHIFT_PENDING and
                            models.Shifts.audienceType == constants.AUDIENCE_TYPE_MARKET
                    ),
                    (
                            contractor.id == any_(models.Hotels.favouriteContractors) and
                            models.Shifts.status == constants.SHIFT_PENDING and
                            models.Shifts.audienceType == constants.AUDIENCE_TYPE_FAVOURITE
                    )
                )
            )
    elif user.userType == constants.MANAGER:
        shifts = db.query(models.Shifts).filter(
            models.Shifts.hotel_id == hotel.id,
            models.Shifts.active == True,
            models.Shifts.createdBy == user.id
        )
        if audience is not None:
            shifts = shifts.filter(
                models.Shifts.hotel_id == hotel.id,
                models.Shifts.active == True,
                models.Shifts.audienceType == audience
            )
    else:
        shifts = db.query(models.Shifts).filter(
            models.Shifts.active == True,
            models.Shifts.hotel_id == hotel.id,
        )
        if audience is not None:
            shifts = shifts.filter(
                models.Shifts.hotel_id == hotel.id,
                models.Shifts.active == True,
                models.Shifts.audienceType == audience
            )

    if role_id is not None:
        shifts = shifts.filter(
            models.Shifts.hotel_id == hotel.id,
            models.Shifts.active == True,
            role_id == any_(models.Shifts.roles_ids)
        )

    if date is not None:
        total = [item for item in shifts.all() if item.createdAt.date() == date]
        part = total[(page - 1) * PAGE_LIMIT:]
        final = part[:PAGE_LIMIT]
        return Pagination(
            data=final,
            count=len(total)
        )

    else:
        return Pagination(
            data=shifts.offset(
                (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all(),
            count=shifts.count()
        )


def get_shift(db: Session, user: models.User, shift_id: int) -> models.Shifts:
    if user.userType == constants.MANAGER:
        shift = db.query(models.Shifts).filter(
            models.Shifts.active == True,
            models.Shifts.id == shift_id,
            models.Shifts.createdBy == user.id
        ).first()
        check_found(shift, "Shift")
        return shift


    elif user.userType == constants.CONTRACTOR:
        shift = db.query(models.Shifts).filter(
            models.Shifts.active == True,
            models.Shifts.id == shift_id
        ).first()

    else:
        shift = db.query(models.Shifts).filter(
            models.Shifts.id == shift_id
        ).first()

    check_found(shift, "Shift")

    return shift


def edit_shift(db: Session, user: models.User, request: schemas.ShiftEdit, shift_id: int) -> models.Shifts:
    shift = get_shift(db, user, shift_id)
    if user.userType == constants.MANAGER:
        if not shift.createdBy == user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Shift not found')

    if not shift.status == constants.SHIFT_PENDING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Shift cannot be edited because is has either been completed, awarded, is ongoing')

    if request.startTime:
        tzone = request.startTime.tzinfo

        if datetime.now(tz=tzone) > request.startTime:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Shift start time cannot be in the past')

        if request.startTime > shift.endTime:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Shift start time has to be higher than endtime')

    if request.endTime:
        tzone = request.endTime.tzinfo

        if datetime.now(tz=tzone) > request.endTime:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Shift end time cannot be in the past')

        if shift.startTime > request.endTime:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Shift start time has to be lower than endtime')

    if request.roles_ids is not None:
        for role_id in request.roles_ids:
            get_jobrole(db, role_id)

    if request.requiredCertificatesTypes is not None:
        for certificate in request.requiredCertificatesTypes:
            get_certificate(db, user, certificate)

    if request.name is not None:
        shift.name = request.name

    if request.roles_ids is not None:
        if shift.roles_ids is None:
            shift.roles_ids = request.roles_ids
        else:
            for role_id in request.roles_ids:
                if role_id not in shift.roles_ids:
                    shift.roles_ids.append(role_id)

    if request.requiredCertificatesTypes is not None:
        if shift.requiredCertificatesTypes is None:
            shift.requiredCertificatesTypes = request.requiredCertificatesTypes
        else:
            for certificate in request.requiredCertificatesTypes:
                if not certificate in shift.requiredCertificatesTypes:
                    shift.requiredCertificatesTypes.append(certificate)

    if request.targetAudience is not None:
        if shift.targetAudience is None:
            shift.targetAudience = request.targetAudience
        else:
            for audience in request.targetAudience:
                if not audience in shift.targetAudience:
                    shift.targetAudience.append(audience)

    if request.pay is not None:
        shift.pay = request.pay
    if request.instructions is not None:
        shift.instructions = request.instructions

    if request.startTime is not None:
        shift.startTime = request.startTime
    if request.endTime is not None:
        shift.endTime = request.endTime

    # if request.startTime is not None and request.endTime is not None:
    #     shift.active = True

    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def delete_shift(db: Session, user: models.User, shift_id: int) -> bool:
    shift = get_shift(db, user, shift_id)

    if shift.status == constants.SHIFT_COMPLETED or shift.status == constants.SHIFT_ONGOING:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='You cannot delete a completed or ongoing shift')

    if user.userType == constants.MANAGER:
        if not shift.createdBy == user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Shift not found')

    if shift.contractor_id is not None:
        time_left = shift.startTime - timedelta(hours=24)
        if datetime.now() > time_left:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can only delete an awarded shift 24 hours before it start time"
            )

        contractor = get_single_verified_contractor(db, shift.contractor_id)
        contractor_user = get_user_by_id(db, contractor.userID)
        notification_settings = get_notification_setting(db, contractor_user)
        title = 'Shift Deleted'
        message = f"The Shift with name '{shift.name}' has been deleted"
        save_notification(
            db,
            title,
            message,
            contractor_user.id
        )
        if notification_settings.push:
            notification.send_firebase_auto_push_notification.apply_async(kwargs={
                'title': title,
                'message': message,
                'user_id': contractor_user.id
            })

        if notification_settings.email:
            email.send_email_auto_notification.apply_async(args=[
                title,
                message,
                contractor_user.email
            ])

    shift.active = False
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return True


def start_shift(db: Session, user: models.User, request: schemas.ClockIn) -> bool:
    contractor = get_contractor_by_user_id(db, user.id)
    shift = get_shift(db, user, request.shift_id)
    if not shift.contractor_id == contractor.id:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Cannot start a shift you have not been awarded')

    if shift.startedAt is not None:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Shift already started')

    allowed_time = shift.startTime - timedelta(minutes=10)
    if allowed_time > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='You can only clock in 10 before the shift')

    shift.startedAt = datetime.utcnow()
    shift.status = constants.SHIFT_ONGOING
    shift.clockInLatitude = request.clockInLatitude
    shift.clockInLongitude = request.clockInLongitude
    db.add(shift)
    db.commit()
    db.refresh(shift)

    manager_user = get_user_by_id(db, shift.createdBy)
    notification_settings = get_notification_setting(db, manager_user)
    if notification_settings.begins_shift:
        send_manager_notification(db, shift, constants.SHIFT_BEGIN)

    return shift


def end_shift(db: Session, user: models.User, request: schemas.ClockOut) -> bool:
    contractor = get_contractor_by_user_id(db, user.id)
    shift = get_shift(db, user, request.shift_id)
    if not shift.contractor_id == contractor.id:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Cannot start a shift you have not been awarded')

    if shift.startedAt is None:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='Shift has not started')

    shift.endedAt = datetime.utcnow()

    # check if contractor forgets to end shift or contractor ends the shift lately.
    if shift.endTime < shift.endedAt:
        shift.endedAt = shift.endTime

    shift.status = constants.SHIFT_COMPLETED
    shift.clockOutLatitude = request.clockOutLatitude
    shift.clockOutLongitude = request.clockOutLongitude

    payPerHour = shift.pay
    duration = abs(shift.endedAt - shift.startedAt)
    total_hours = duration.total_seconds() / 3600
    rounded_hours = round(total_hours, 2)  # rounded to two decimal places
    total = payPerHour * rounded_hours
    shift2GoPercentage = SHIFT2GO_PERCENTAGE / 100
    shift2Go_share = total * shift2GoPercentage

    # generate bill
    bill_in = schemas.BillingIn(
        shift_id=shift.id,
        hotel_id=shift.hotel_id,
        status=constants.BILLING_PENDING,
        # paymentTransactionID=request.paymentTransactionID,
        amountPayableToShift2go=shift2Go_share,
        amountPayableToContractor=total - shift2Go_share

    )
    bill = create_bill(db, user, bill_in)
    check_found(bill, 'Billing ')

    db.add(shift)
    db.commit()
    db.refresh(shift)

    contractor_user = get_user_by_id(db, contractor.userID)
    notification_settings = get_notification_setting(db, contractor_user)
    completed_message = generate_shift_clockout_notification_message(
        shift, contractor_user, bill)
    save_notification(
        db,
        constants.SHIFT_COMPLETED_NOTIFICATION_TITLE,
        completed_message,
        contractor_user.id
    )
    if notification_settings.push:
        notification.send_firebase_auto_push_notification.apply_async(kwargs={
            'title': constants.SHIFT_COMPLETED_NOTIFICATION_TITLE,
            'message': completed_message,
            'user_id': contractor_user.id
        })

    if notification_settings.email:
        email.send_email_auto_notification.apply_async(args=[
            constants.SHIFT_COMPLETED_NOTIFICATION_TITLE,
            completed_message,
            contractor_user.email
        ])

    manager_user = get_user_by_id(db, shift.createdBy)
    save_notification(
        db,
        constants.SHIFT_COMPLETED_NOTIFICATION_TITLE,
        completed_message,
        manager_user.id
    )
    notification_settings = get_notification_setting(db, contractor_user)
    manager_message = generate_shift_completed_notification_message(
        shift, contractor_user)
    if notification_settings.push:
        notification.send_firebase_auto_push_notification.apply_async(kwargs={
            'title': constants.SHIFT_COMPLETED_NOTIFICATION_TITLE,
            'message': manager_message,
            'user_id': manager_user.id
        })

    if notification_settings.email:
        email.send_email_auto_notification.apply_async(args=[
            constants.SHIFT_COMPLETED_NOTIFICATION_TITLE,
            manager_message,
            manager_user.email
        ])

    manager_user = get_user_by_id(db, shift.createdBy)
    notification_settings = get_notification_setting(db, manager_user)
    if notification_settings.ends_shift:
        send_manager_notification(db, shift, constants.SHIFT_END)

    return shift


def cancel_shift(db: Session, user: models.User, request: schemas.CancellationIn) -> models.ShiftCancellations:
    shift = get_shift_by_id(db, request.shift_id)
    if user.userType == constants.CONTRACTOR:
        contractor = get_contractor(db, user)

        if shift.contractor_id != contractor.id and shift.status != constants.SHIFT_ACCEPTED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Not allowed to cancel a shift you have not been awarded and accepted')

    cancellation = models.ShiftCancellations(
        cancelledBy=user.id,
        shift_id=shift.id,
        reason=request.reason
    )

    db.add(cancellation)
    db.commit()
    db.refresh(cancellation)

    shift.contractor_id = None
    shift.status = constants.SHIFT_PENDING
    db.add(shift)
    db.commit()

    manager_user = get_user_by_id(db, shift.createdBy)
    notification_settings = get_notification_setting(db, manager_user)
    if notification_settings.cancels_shift:
        send_manager_notification(
            db,
            shift,
            constants.SHIFT_CANCEL
        )

    return cancellation


def get_cancellations(db: Session, user: models.User, page: int, user_id: int = None) -> Pagination:
    if user.userType == constants.CONTRACTOR:
        cancels = db.query(models.ShiftCancellations).filter(
            models.ShiftCancellations.cancelledBy == user.id
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.ShiftCancellations).filter(
            models.ShiftCancellations.cancelledBy == user.id
        ).count()
        return Pagination(data=cancels, count=count)

    if user.userType == constants.MANAGER:
        cancels: Query = db.query(models.ShiftCancellations).join(
            models.Shifts,
            models.Shifts.id == models.ShiftCancellations.shift_id
        ).filter(models.Shifts.createdBy == user.id)

        if user_id:
            cancels = cancels.filter(
                models.ShiftCancellations.cancelledBy == user_id
            )
        count = cancels.count()
        cancels = cancels.offset(
            (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        return Pagination(data=cancels, count=count)

    # if user.userType == constants.MANAGER and user_id is None:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
    #                         detail='Hotel mangers should pass in user_id')
    if user_id:
        cancels = db.query(models.ShiftCancellations).filter(
            models.ShiftCancellations.cancelledBy == user_id
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.ShiftCancellations).filter(
            models.ShiftCancellations.cancelledBy == user_id
        ).count()
        return Pagination(data=cancels, count=count)

    cancels = db.query(models.ShiftCancellations).offset(
        (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.ShiftCancellations).count()
    return Pagination(data=cancels, count=count)


def get_cancellation(db: Session, user: models.User, cancelled_id: int) -> models.ShiftCancellations:
    if user.userType == constants.CONTRACTOR:
        cancel = db.query(models.ShiftCancellations).filter(
            models.ShiftCancellations.cancelledBy == user.id,
            models.ShiftCancellations.id == cancelled_id
        ).first()
        check_found(cancel, 'Shift Cancellation')
        return cancel

    cancelled = db.query(models.ShiftCancellations).filter(
        models.ShiftCancellations.id == cancelled_id
    ).first()
    check_found(cancelled, 'Shift Cancellation')
    return cancelled


def edit_cancellation(db: Session, user: models.User, request: schemas.CancellationEdit,
                      cancelled_id: int) -> models.ShiftCancellations:
    cancelled = get_cancellation(db, user, cancelled_id)

    if request.reason:
        cancelled.reason = request.reason

    db.add(cancelled)
    db.commit()
    db.refresh(cancelled)
    return cancelled


def create_bill(db: Session, user: models.User, request: schemas.BillingIn) -> models.Billings:
    shift = get_shift(db, user, request.shift_id)
    hotel = get_hotel_by_id(db, request.hotel_id)
    bill = models.Billings(
        shift_id=shift.id,
        hotel_id=hotel.id,
        status=request.status,
        paymentTransactionID=request.paymentTransactionID,
        createdBy=user.id,
        amountPayableToShift2go=request.amountPayableToShift2go,
        amountPayableToContractor=request.amountPayableToContractor
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def get_bills(db: Session, user: models.User, page: int, start_date: date, end_date: date) -> Pagination:
    if not (start_date is None and end_date is None):
        if (start_date is None and end_date is not None) or (end_date is None and start_date is not None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='You should pass both end and start dates')

        if end_date == start_date or end_date < start_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='End date should be greater than start date')

    if not user.userType == constants.ADMIN:
        if start_date is not None:
            bills = db.query(models.Billings).join(
                models.Shifts,
                models.Shifts.id == models.Billings.shift_id
            ).filter(
                or_(
                    models.Shifts.createdBy == user.id,
                    models.Billings.createdBy == user.id,
                ),
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).join(
                models.Shifts,
                models.Shifts.id == models.Billings.shift_id
            ).filter(
                or_(
                    models.Shifts.createdBy == user.id,
                    models.Billings.createdBy == user.id,
                ),
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).count()
            return Pagination(data=bills, count=count)
        else:
            bills = db.query(models.Billings).join(
                models.Shifts,
                models.Shifts.id == models.Billings.shift_id
            ).filter(
                or_(
                    models.Shifts.createdBy == user.id,
                    models.Billings.createdBy == user.id,
                )
            ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).join(
                models.Shifts,
                models.Shifts.id == models.Billings.shift_id
            ).filter(
                or_(
                    models.Shifts.createdBy == user.id,
                    models.Billings.createdBy == user.id,
                )
            ).count()
            return Pagination(data=bills, count=count)
    else:
        if start_date is not None:
            bills = db.query(models.Billings).filter(
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).offset(
                (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).filter(
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).count()
            return Pagination(data=bills, count=count)
        else:
            bills = db.query(models.Billings).offset(
                (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).count()
            return Pagination(data=bills, count=count)


def get_hotel_bills(db: Session, user: models.User, page: int, start_date: date, end_date: date,
                    hotel_id: int) -> Pagination:
    hotel = get_hotel_by_id_and_user(db, user, hotel_id)

    if not (start_date is None and end_date is None):
        if (start_date is None and end_date is not None) or (end_date is None and start_date is not None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='You should pass both end and start dates')

        if end_date == start_date or end_date < start_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='End date should be greater than start date')

    if not user.userType == constants.ADMIN:
        if start_date is not None:
            bills = db.query(models.Billings).filter(
                models.Billings.createdBy == user.id,
                models.Billings.hotel_id == hotel.id,
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).filter(
                models.Billings.createdBy == user.id,
                models.Billings.hotel_id == hotel.id,
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).count()
            return Pagination(data=bills, count=count)
        else:
            bills = db.query(models.Billings).filter(
                models.Billings.hotel_id == hotel.id,
                models.Billings.createdBy == user.id
            ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).filter(
                models.Billings.hotel_id == hotel.id,
                models.Billings.createdBy == user.id
            ).count()
            return Pagination(data=bills, count=count)
    else:
        if start_date is not None:
            bills = db.query(models.Billings).filter(
                models.Billings.hotel_id == hotel.id,
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).offset(
                (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).filter(
                models.Billings.hotel_id == hotel.id,
                and_(
                    models.Billings.createdAt > start_date,
                    end_date > models.Billings.createdAt
                )
            ).count()
            return Pagination(data=bills, count=count)
        else:
            bills = db.query(models.Billings).filter(
                models.Billings.hotel_id == hotel.id
            ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
            count = db.query(models.Billings).filter(
                models.Billings.hotel_id == hotel.id
            ).count()
            return Pagination(data=bills, count=count)


def get_bill(db: Session, user: models.User, bill_id: int) -> models.Billings:
    bill: models.Billings = None
    if not user.userType == constants.ADMIN:
        bill = db.query(models.Billings).join(
            models.Shifts,
            models.Shifts.id == models.Billings.shift_id
        ).filter(
            or_(
                models.Shifts.createdBy == user.id,
                models.Billings.createdBy == user.id,
            ),
            models.Billings.id == bill_id
        ).first()
        check_found(bill, 'Billing')
        return bill

    bill = db.query(models.Billings).filter(
        models.Billings.id == bill_id,
    ).first()
    check_found(bill, 'Billing')
    return bill


def delete_bill(db: Session, user: models.User, bill_id: int) -> bool:
    bill = get_bill(db, user, bill_id)
    if not user.userType == constants.ADMIN:
        if not bill.createdBy == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Billing not found')

    db.delete(bill)
    db.commit()
    return True


def edit_billing(db: Session, user: models.User, request: schemas.BillingEdit, bill_id: int) -> models.Billings:
    if request.status not in [constants.BILLING_PENDING, constants.BILLING_PAID]:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE, detail='billing status should be either PENDING or PAID'
        )
    bill = get_bill(db, user, bill_id)
    if not user.userType == constants.ADMIN:
        if not bill.createdBy == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Billing not found')
    bill.status = request.status
    if request.status is not None:
        bill.status = request.status

    if request.paymentTransactionID is not None:
        bill.paymentTransactionID = request.paymentTransactionID

    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def create_notification(db: Session, user: models.User, request: schemas.NotificationIn) -> models.Notifications:
    if len(request.receivers) < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='There should be at least one receiver')
    for id in request.receivers:
        get_user_by_id(db, id)
    notification = models.Notifications(
        message=request.message,
        title=request.title,
        receivers=request.receivers,
        notificationType=request.notificationType,
        createdBy=user.id
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notification(db: Session, user: models.User, notification_id: int) -> models.Notifications:
    if user.userType == constants.CONTRACTOR:
        notification = db.query(models.Notifications).filter(
            user.id == any_(models.Notifications.receivers),
            models.Notifications.id == notification_id
        ).first()
        check_found(notification, 'Notification')
        return notification

    elif user.userType == constants.MANAGER:
        notification = db.query(models.Notifications).filter(
            models.Notifications.createdBy == user.id,
            models.Notifications.id == notification_id
        ).first()
        check_found(notification, 'Notification')
        return notification

    else:
        notification = db.query(models.Notifications).filter(
            models.Notifications.id == notification_id
        ).first()
        check_found(notification, 'Notification')
        return notification


def get_notifications(db: Session, user: models.User, page: int) -> Pagination:
    if user.userType == constants.CONTRACTOR:
        notifications = db.query(models.Notifications).filter(
            or_(
                user.id == any_(models.Notifications.receivers),
                user.id == models.Notifications.createdBy
            )
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.Notifications).filter(
            or_(
                user.id == any_(models.Notifications.receivers),
                user.id == models.Notifications.createdBy
            )
        ).count()
        return Pagination(data=notifications, count=count)

    elif user.userType == constants.MANAGER:
        notifications = db.query(models.Notifications).filter(
            models.Notifications.createdBy == user.id
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.Notifications).filter(
            models.Notifications.createdBy == user.id
        ).count()
        return Pagination(data=notifications, count=count)

    else:
        notifications = db.query(models.Notifications).offset(
            (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.Notifications).count()
        return Pagination(data=notifications, count=count)


def create_country(db: Session, request: schemas.CountryIn) -> models.Country:
    try:
        country = models.Country(
            **request.dict()
        )
        db.add(country)
        db.commit()
        db.refresh(country)
        return country
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(error))


def get_countries(db: Session) -> t.List[models.Country]:
    return db.query(models.Country).all()


def get_country(db: Session, country_code: str) -> models.Country:
    country = db.query(models.Country).filter(
        models.Country.code == country_code
    ).first()
    check_found(country, 'Country')
    return country


def create_document(db: Session, user: models.User, request: schemas.DocumentsIn) -> models.Documents:
    document = models.Documents(
        url=request.url,
        createdBy=user.id
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, user: models.User, document_id: int) -> models.Documents:
    if user.userType == constants.MANAGER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Not Allowed')
    if user.userType == constants.CONTRACTOR:
        document = db.query(models.Documents).filter(
            models.Documents.id == document_id,
            models.Documents.createdBy == user.id,
        ).first()
        check_found(document, 'Document')
        return document

    document = db.query(models.Documents).filter(
        models.Documents.id == document_id
    ).first()
    check_found(document, 'Document')
    return document


def get_documents(db: Session, user: models.User) -> t.List[models.Documents]:
    if user.userType == constants.MANAGER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Not Allowed')
    if user.userType == constants.CONTRACTOR:
        document = db.query(models.Documents).filter(
            models.Documents.createdBy == user.id,
        ).all()
        return document

    document = db.query(models.Documents).all()
    return document


def edit_document(db: Session, user: models.User, request: schemas.DocumentsEdit, document_id: int) -> models.Documents:
    if user.userType == constants.CONTRACTOR:
        if request.verified is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Only Admin change verification status')
        if request.url is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Contractor needs to pass url')

    document = get_document(db, user, document_id)
    check_found(document, 'Document')

    if request.verified is not None:
        document.verified = request.verified
    if request.url is not None:
        document.url = request.url

    return document


def create_request(db: Session, user: models.User, request: schemas.ShiftRequestIn) -> models.ShiftRequests:
    shift = get_shift_by_id(db, request.shift_id)
    if shift.contractor_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Shift has already been assigned')

    old_request = db.query(models.ShiftRequests).filter(
        models.ShiftRequests.createdBy == user.id,
        models.ShiftRequests.shift_id == shift.id
    ).first()

    if old_request:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='You have already requested this Shift')

    if datetime.now() > shift.startTime:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Shift has already started')

    shift_request = models.ShiftRequests(
        notes=request.notes,
        shift_id=request.shift_id,
        createdBy=user.id
    )
    db.add(shift_request)
    db.commit()
    db.refresh(shift_request)

    contractor_user = get_user_by_id(db, user.id)
    manager_user = get_user_by_id(db, shift.createdBy)
    notification_settings = get_notification_setting(db, manager_user)
    request_message = generate_shift_request_notification_message(
        shift, contractor_user)
    save_notification(
        db,
        constants.SHIFT_REQUEST_NOTIFICATION_TITLE,
        request_message,
        manager_user.id
    )
    if notification_settings.push:
        notification.send_firebase_auto_push_notification.apply_async(kwargs={
            'title': constants.SHIFT_REQUEST_NOTIFICATION_TITLE,
            'message': request_message,
            'user_id': manager_user.id
        })

    if notification_settings.email:
        email.send_email_auto_notification.apply_async(args=[
            constants.SHIFT_REQUEST_NOTIFICATION_TITLE,
            request_message,
            manager_user.email
        ])

    return shift_request


def get_requests(db: Session, user: models.User, page: int) -> Pagination:
    if user.userType == constants.MANAGER:
        # get requests to his hotels
        get_manager_by_user_id(db, user.id)
        requests = db.query(models.ShiftRequests).join(
            models.Shifts,
            models.Shifts.id == models.ShiftRequests.shift_id
        ).join(
            models.Hotels,
            models.Hotels.id == models.Shifts.hotel_id
        ).filter(
            models.Hotels.createdBy == user.id
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.ShiftRequests).join(
            models.Shifts,
            models.Shifts.id == models.ShiftRequests.shift_id
        ).join(
            models.Hotels,
            models.Hotels.id == models.Shifts.hotel_id
        ).count()
        return Pagination(data=requests, count=count)
    elif user.userType == constants.CONTRACTOR:
        requests = db.query(models.ShiftRequests).filter(
            models.ShiftRequests.createdBy == user.id
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.ShiftRequests).filter(
            models.ShiftRequests.createdBy == user.id
        ).count()
        return Pagination(data=requests, count=count)

    else:
        requests = db.query(models.ShiftRequests).offset(
            (page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.ShiftRequests).count()
        return Pagination(data=requests, count=count)


def get_request(db: Session, user: models.User, request_id: int) -> models.ShiftRequests:
    if user.userType == constants.MANAGER:
        # get requests to his hotels
        manager = get_manager_by_user_id(db, user.id)
        request = db.query(models.ShiftRequests).join(
            models.Shifts,
            models.Shifts.id == models.ShiftRequests.shift_id
        ).join(
            models.Hotels,
            models.Hotels.id == models.Shifts.hotel_id
        ).filter(
            models.Hotels.createdBy == user.id,
            models.ShiftRequests.id == request_id
        ).first()
        check_found(request, 'Shift Request')
        return request
    elif user.userType == constants.CONTRACTOR:
        request = db.query(models.ShiftRequests).filter(
            models.ShiftRequests.id == request_id,
            models.ShiftRequests.createdBy == user.id
        ).first()
        check_found(request, 'Shift Request')
        return request

    else:
        request = db.query(models.ShiftRequests).filter(
            models.ShiftRequests.id == request_id,
        ).first()
        check_found(request, 'Shift Request')
        return request


def edit_request(db: Session, user: models.User, request: schemas.ShiftRequestEdit,
                 request_id: int) -> models.ShiftRequests:
    shift_request = get_request(db, user, request_id)
    shift_request.notes = request.notes
    db.add(shift_request)
    db.commit()
    db.refresh(shift_request)
    return shift_request


def delete_request(db: Session, user: models.User, request_id: int) -> bool:
    request = get_request(db, user, request_id)
    db.delete(request)
    db.commit()
    return True


def get_notification_setting(db: Session, user: models.User) -> models.NotificationSettings:
    settings = db.query(models.NotificationSettings).filter(
        models.NotificationSettings.createdBy == user.id
    ).first()
    if not settings:
        settings = models.NotificationSettings(
            email=True,
            push=True,
            reminder=1,
            createdBy=user.id
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def update_notification_setting(db: Session, user: models.User,
                                request: schemas.NotificationSettingsEdit) -> models.NotificationSettings:
    settings = db.query(models.NotificationSettings).filter(
        models.NotificationSettings.createdBy == user.id
    ).first()
    if not settings:
        settings = models.NotificationSettings(
            email=True,
            push=True,
            createdBy=user.id
        )

    if request.email is not None:
        settings.email = request.email
    if request.push is not None:
        settings.push = request.push
    if request.cancels_shift is not None:
        settings.cancels_shift = request.cancels_shift
    if request.ends_shift is not None:
        settings.ends_shift = request.ends_shift
    if request.begins_shift is not None:
        settings.begins_shift = request.begins_shift
    if request.accepts_shift is not None:
        settings.accepts_shift = request.accepts_shift
    if request.declines_shift is not None:
        settings.declines_shift = request.declines_shift

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def accept_shift(db, user: models.User, shift_id: int) -> models.Shifts:
    contractor = get_contractor(db, user)
    shift = get_shift_by_id(db, shift_id)
    if not shift.contractor_id == contractor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Cannot accept a shift you have not been assigned to')
    if shift.status == constants.SHIFT_ACCEPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Shift already accepted')
    shift.status = constants.SHIFT_ACCEPTED
    db.add(shift)
    db.commit()
    db.refresh(shift)

    contractor_user = get_user_by_id(db, contractor.userID)
    manager_user = get_user_by_id(db, shift.createdBy)
    notification_settings = get_notification_setting(db, manager_user)
    when = shift.startTime - timedelta(hours=notification_settings.reminder)
    if datetime.utcnow() > when:
        when = datetime.utcnow() + timedelta(seconds=30)
    accept_message = generate_accepted_shift_notification_message(
        shift, contractor_user)
    save_notification(
        db,
        constants.ACCEPTED_SHIFT_NOTIFICATION_TITLE,
        accept_message,
        manager_user.id
    )
    if notification_settings.push:
        notification.send_firebase_auto_push_notification.apply_async(kwargs={
            'title': constants.ACCEPTED_SHIFT_NOTIFICATION_TITLE,
            'message': accept_message,
            'user_id': manager_user.id
        })

    if notification_settings.email:
        email.send_email_auto_notification.apply_async(args=[
            constants.ACCEPTED_SHIFT_NOTIFICATION_TITLE,
            accept_message,
            manager_user.email
        ])

    upcoming_message = generate_upcoming_shift_notification_message(
        shift, contractor_user)
    save_notification(
        db,
        constants.UPCOMING_SHIFT_NOTIFICATION_TITLE,
        accept_message,
        manager_user.id
    )
    notification_settings = get_notification_setting(db, contractor_user)
    if notification_settings.push:
        notification.send_firebase_auto_push_notification.apply_async(kwargs={
            'title': constants.UPCOMING_SHIFT_NOTIFICATION_TITLE,
            'message': upcoming_message,
            'user_id': contractor_user.id
        }, eta=when)

    if notification_settings.email:
        email.send_email_auto_notification.apply_async(args=[
            constants.UPCOMING_SHIFT_NOTIFICATION_TITLE,
            upcoming_message,
            contractor_user.email
        ], eta=when)

    manager_user = get_user_by_id(db, shift.createdBy)
    notification_settings = get_notification_setting(db, manager_user)
    if notification_settings.accepts_shift:
        send_manager_notification(db, shift, constants.SHIFT_ACCEPT)

    return shift


def decline_shift(db, user: models.User, shift_id: int) -> models.Shifts:
    contractor = get_contractor(db, user)
    shift = get_shift_by_id(db, shift_id)
    if not shift.contractor_id == contractor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Cannot decline a shift you have not been assigned to')
    shift.status = constants.SHIFT_PENDING
    shift.contractor_id = None
    if shift.audienceType == constants.AUDIENCE_TYPE_MANUAL:
        shift.audienceType == constants.AUDIENCE_TYPE_MARKET
    db.add(shift)
    db.commit()
    db.refresh(shift)

    contractor_user = get_user_by_id(db, contractor.userID)
    manager_user = get_user_by_id(db, shift.createdBy)
    decline_message = generate_decline_shift_notification_message(
        shift, contractor_user)
    save_notification(
        db,
        constants.DECLINE_SHIFT_NOTIFICATION_TITLE,
        decline_message,
        manager_user.id
    )
    notification_settings = get_notification_setting(db, manager_user)
    if notification_settings.push:
        notification.send_firebase_auto_push_notification.apply_async(kwargs={
            'title': constants.DECLINE_SHIFT_NOTIFICATION_TITLE,
            'message': decline_message,
            'user_id': manager_user.id
        })

    if notification_settings.email:
        email.send_email_auto_notification.apply_async(args=[
            constants.DECLINE_SHIFT_NOTIFICATION_TITLE,
            generate_decline_shift_notification_message(
                shift, contractor_user),
            manager_user.email
        ])

    manager_user = get_user_by_id(db, shift.createdBy)
    notification_settings = get_notification_setting(db, manager_user)
    if notification_settings.declines_shift:
        send_manager_notification(db, shift, constants.SHIFT_DECLINE)

    return shift


def accepted_shifts(db, user: models.User, page: int) -> Pagination:
    contractor = get_contractor(db, user)
    shift = db.query(models.Shifts).filter(
        models.Shifts.contractor_id == contractor.id,
        models.Shifts.status == constants.SHIFT_ACCEPTED
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Shifts).filter(
        models.Shifts.contractor_id == contractor.id,
        models.Shifts.status == constants.SHIFT_ACCEPTED
    ).count()
    return Pagination(data=shift, count=count)


def contractor_upcoming_shift(db: Session, user: models.User, page: int, contractor_id: int = None) -> Pagination:
    if user.userType == constants.ADMIN and contractor_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Admin should pass contractor_id')
    if user.userType == constants.CONTRACTOR and contractor_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Contractor should not pass contractor_id')

    contractor = get_single_verified_contractor(
        db, contractor_id) if user.userType == constants.ADMIN else get_contractor_by_user_id(db, user.id)
    shifts = db.query(models.Shifts).filter(
        models.Shifts.contractor_id == contractor.id,
        models.Shifts.status == constants.SHIFT_ACCEPTED,
        models.Shifts.startTime > datetime.utcnow()
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Shifts).filter(
        models.Shifts.contractor_id == contractor.id
    ).count()
    return Pagination(data=shifts, count=count)


def contractor_ongoing_shift(db: Session, user: models.User, contractor_id: int = None) -> t.List[models.Shifts]:
    if user.userType == constants.ADMIN and contractor_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Admin should pass contractor_id')
    if user.userType == constants.CONTRACTOR and contractor_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Contractor should not pass contractor_id')

    contractor = get_single_verified_contractor(
        db, contractor_id) if user.userType == constants.ADMIN else get_contractor_by_user_id(db, user.id)
    return db.query(models.Shifts).filter(
        models.Shifts.contractor_id == contractor.id,
        models.Shifts.status == constants.SHIFT_ONGOING,
        models.Shifts.startedAt is not None
    ).all()


def hotel_ongoing_shift(db: Session, user: models.User, hotel_id: int) -> t.List[models.Shifts]:
    hotel = get_hotel_by_id_and_user(db, user, hotel_id)
    return db.query(models.Shifts).filter(
        models.Shifts.hotel_id == hotel.id,
        models.Shifts.status == constants.SHIFT_ONGOING,
        models.Shifts.startedAt is not None
    ).all()


def contractor_shift_history(db: Session, user: models.User, page: int, contractor_id: int = None) -> Pagination:
    if user.userType == constants.ADMIN and contractor_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Admin should pass contractor_id')
    if user.userType == constants.CONTRACTOR and contractor_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Contractor should not pass contractor_id')

    contractor = get_single_verified_contractor(
        db, contractor_id) if user.userType == constants.ADMIN else get_contractor_by_user_id(db, user.id)
    cancelled_shifts = db.query(models.ShiftCancellations).filter(
        models.ShiftCancellations.cancelledBy == contractor.userID
    ).all()
    cancelled_shifts_ids = [shift.shift_id for shift in cancelled_shifts]
    shifts = db.query(models.Shifts).filter(
        or_(
            models.Shifts.id == any_(cancelled_shifts_ids),
            and_(
                models.Shifts.contractor_id == contractor.id,
                models.Shifts.status == constants.SHIFT_COMPLETED
            ),
        ),
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Shifts).filter(
        models.Shifts.id == any_(cancelled_shifts_ids),
        models.Shifts.contractor_id == contractor.id,
    ).count()
    return Pagination(data=shifts, count=count)


def create_certificate_type(db: Session, request: schemas.CertificateTypeIn) -> models.CertificateTypes:
    db_certificate_type = models.CertificateTypes(
        name=request.name
    )
    db.add(db_certificate_type)
    db.commit()
    db.refresh(db_certificate_type)
    return db_certificate_type


def get_certificate_types(db: Session) -> t.List[models.CertificateTypes]:
    certificate_type = db.query(models.CertificateTypes).all()
    return certificate_type


def get_a_certificate_type(db: Session, certificate_type_id: int) -> models.CertificateTypes:
    certificate_type = db.query(models.CertificateTypes).filter(
        models.CertificateTypes.id == certificate_type_id).first()
    check_found(certificate_type, 'Certificate Type')
    return certificate_type


def edit_certificate_type(db: Session, request: schemas.CertificateTypeEdit) -> models.CertificateTypes:
    certificate_type = get_a_certificate_type(db, request.id)
    certificate_type.name = request.name
    db.add(certificate_type)
    db.commit()
    db.refresh(certificate_type)
    return certificate_type


def award_a_shift(db: Session, user: models.User, request: schemas.AwardShift) -> models.Shifts:
    contractor = get_single_verified_contractor(db, request.contractor_id)
    shift = get_shift_by_id(db, request.shift_id)
    if shift.active == False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='You cannot award a shift which is not active')
    if user.userType == constants.MANAGER:
        if not shift.createdBy == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Manager does not own this shift')

    shift.contractor_id = request.contractor_id

    db.add(shift)
    db.commit()
    db.refresh(shift)

    contractor_user = get_user_by_id(db, contractor.userID)
    notification_settings = get_notification_setting(db, contractor_user)
    award_message = generate_awarded_shift_notification_message(
        shift, contractor_user)
    save_notification(
        db,
        constants.AWARDED_SHIFT_NOTIFICATION_TITLE,
        award_message,
        contractor_user.id
    )
    if notification_settings.push:
        notification.send_firebase_auto_push_notification.apply_async(kwargs={
            'title': constants.AWARDED_SHIFT_NOTIFICATION_TITLE,
            'message': award_message,
            'user_id': contractor_user.id
        })

    if notification_settings.email:
        email.send_email_auto_notification.apply_async(args=[
            constants.AWARDED_SHIFT_NOTIFICATION_TITLE,
            award_message,
            contractor_user.email
        ])

    return shift


def update_remainder_hours(db: Session, user: models.User, request: schemas.Hours) -> models.NotificationSettings:
    settings = get_notification_setting(db, user)
    settings.reminder = request.hours
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def get_cancellation_status(db: Session, user: models.User, shift_id: int) -> schemas.Penalty:
    shift = get_shift_by_id(db, shift_id)
    penalty_range = shift.startTime - timedelta(hours=12)

    cancellations = db.query(models.ShiftCancellations).filter(
        models.ShiftCancellations.cancelledBy == user.id,
    ).order_by(models.ShiftCancellations.createdAt.desc()).all()

    penalty_cancellations: t.List[models.ShiftCancellations] = []
    for cancelled_item in cancellations:
        shift = get_shift_by_id(db, cancelled_item.shift_id)
        penalty_range = shift.startTime - timedelta(hours=12)
        if cancelled_item.createdAt >= penalty_range:
            penalty_cancellations.append(cancelled_item)

    penalties_len = len(penalty_cancellations)

    if not datetime.utcnow() >= penalty_range:
        return schemas.Penalty(
            existing=penalties_len,
            deadline=penalty_range,
            message='No penalty'
        )

    message: str = 'You will need to call Shift2Go and explain'
    if penalties_len == 0:
        pass
    elif penalties_len == 1:
        first = cancellations[0]
        diff = datetime.utcnow() - first.createdAt
        if diff.days <= 45:
            message = 'You will be suspended for 14 days'
    elif penalties_len == 2:
        first = cancellations[0]
        diff = datetime.utcnow() - first.createdAt
        if diff.days <= 45:
            message = 'You will be suspended for 30 days'
    elif penalties_len == 3:
        message = 'You will be suspended indefinitely. You can also call Shift2Go and explain'
    else:
        message = 'You will be banned from this platform'

    return schemas.Penalty(
        existing=penalties_len,
        deadline=penalty_range,
        message=message
    )


def save_notification(db: Session, title: str, message: str, user_id: int):
    notification = models.Notifications(
        title=title,
        message=message,
        notificationType=constants.NOTIFICATION_SELF,
        createdBy=user_id
    )
    db.add(notification)
    db.commit()


def read_notification(db: Session, user: models.User, notification_id: int) -> models.Notifications:
    notification = get_notification(db, user, notification_id)
    if notification.readBy is None:
        notification.readBy = []
    if user.id in notification.readBy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Notification already read')
    notification.readBy.append(user.id)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def verify_user_manually(db: Session, user_id: int) -> models.User:
    user = get_user_by_id(db, user_id)
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='user already verified')
    user.is_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def platform_summary(db: Session) -> schemas.Summary:
    contractors = db.query(models.Contractors).count()
    shifts = db.query(models.Shifts).count()
    shifts_completed = db.query(models.Shifts).filter(
        models.Shifts.status == constants.SHIFT_COMPLETED
    ).count()
    hotels = db.query(models.Hotels).count()
    return schemas.Summary(
        contractors=contractors,
        hotels=hotels,
        shifts=shifts,
        shifts_completed=shifts_completed
    )


def confirm_shift(db: Session, user: models.User, shift_id: int) -> models.Shifts:
    shift = get_shift(db, user, shift_id)
    if not shift.confirmed and shift.status == constants.SHIFT_COMPLETED:
        shift.confirmed = True
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Already confirmed')

    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def confirmed_shifts(db: Session, user: models.User, page: int) -> Pagination:
    if user.userType == constants.MANAGER:
        shifts = db.query(models.Shifts).filter(
            models.Shifts.createdBy == user.id,
            models.Shifts.confirmed == True
        ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
        count = db.query(models.Shifts).filter(
            models.Shifts.createdBy == user.id,
            models.Shifts.confirmed == True
        ).count()
        return Pagination(data=shifts, count=count)

    shifts = db.query(models.Shifts).filter(
        models.Shifts.confirmed == True
    ).offset((page - 1) * PAGE_LIMIT).limit(PAGE_LIMIT).all()
    count = db.query(models.Shifts).filter(
        models.Shifts.confirmed == True
    ).count()
    return Pagination(data=shifts, count=count)


def set_default_roles(db: Session, user: models.User) -> t.List[models.JobRoles]:
    roles: t.List[dict] = [
        {
            'name': 'Supervisor',
            'image': f'https://firebasestorage.googleapis.com/v0/b/shift2go-app.appspot.com/o/job_roles%2Fsupervisor.png?alt=media&token=33181dc4-1eac-47b6-b960-1377787c1759'
        },
        {
            'name': 'Maintenance',
            'image': f'https://firebasestorage.googleapis.com/v0/b/shift2go-app.appspot.com/o/job_roles%2Fsupervisor.png?alt=media&token=33181dc4-1eac-47b6-b960-1377787c1759'
        },
        {
            'name': 'House Keeper',
            'image': f'https://firebasestorage.googleapis.com/v0/b/shift2go-app.appspot.com/o/job_roles%2Fhousekeeper8.png?alt=media&token=bf14f6da-7deb-4ee4-a5ed-b8c83c64401e'
        },
        {
            'name': 'Front Desk',
            'image': f'https://firebasestorage.googleapis.com/v0/b/shift2go-app.appspot.com/o/job_roles%2Ffront_desk.png?alt=media&token=64601b4c-ab08-46fe-93ce-29b38d08efd8'
        },
        {
            'name': 'Food Handling',
            'image': f'https://firebasestorage.googleapis.com/v0/b/shift2go-app.appspot.com/o/job_roles%2Ffood_handling.png?alt=media&token=e0a60b75-e82a-458b-a1ab-f9999da3c842'
        },
        {
            'name': 'Beverage',
            'image': f'https://firebasestorage.googleapis.com/v0/b/shift2go-app.appspot.com/o/job_roles%2Fbeverage.png?alt=media&token=90848f11-4378-4383-93e8-e1e98f65e4a9'
        },
        {
            'name': 'Bartending',
            'image': f'https://firebasestorage.googleapis.com/v0/b/shift2go-app.appspot.com/o/job_roles%2Fbartender.png?alt=media&token=a331fe9d-7211-4904-b1be-c7e259f5bf57'
        }
    ]
    for role in roles:
        db_role = models.JobRoles(
            name=role['name'],
            image=role['image'],
            createdBy=user.id
        )
        db.add(db_role)
        db.commit()
    return db.query(models.JobRoels).all()


def set_default_certificate_types(db: Session) -> t.List[models.CertificateTypes]:
    certificate_types: t.List = [
        'OnQ',
        'Opera',
        'Synxis',
        'Advantage',
        'Fosse',
        'Springer Miller Systems',
        'ServSave',
        'TIPS On-Premise',
        'TIPS Off-Premise',
    ]
    for name in certificate_types:
        db_type = models.CertificateTypes(
            name=name
        )
        db.add(db_type)
        db.commit()
    return db.query(models.CertificateTypes).all()


def master_reset():
    # drop database
    try:
        drop_database(SQLALCHEMY_DATABASE_URI)
    except:
        pass

    # create database and tables
    if not database_exists(
            SQLALCHEMY_DATABASE_URI
    ):
        create_database(SQLALCHEMY_DATABASE_URI)
    models.Base.metadata.create_all(engine)
    return True
