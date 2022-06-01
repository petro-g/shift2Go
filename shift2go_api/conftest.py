from sqlalchemy.orm import Session
import typing as t
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database, drop_database

from app.db import models, crud
from app.config import config, security, constants
from app.db.session import get_db
from app.db.session import Base
from app.main import app


def get_test_db_url() -> str:
    return f"{config.SQLALCHEMY_DATABASE_URI}_test"


@pytest.fixture
def test_db():
    """
    Modify the db session to automatically roll back after each test.
    This is to avoid tests affecting the database state of other tests.
    """
    # Connect to the test database
    engine = create_engine(
        get_test_db_url(),
    )

    connection = engine.connect()
    trans = connection.begin()

    # Run a parent transaction that can roll back all changes
    test_session_maker = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    test_session: Session = test_session_maker()
    test_session.begin_nested()

    @event.listens_for(test_session, "after_transaction_end")
    def restart_savepoint(s, transaction):
        if transaction.nested and not transaction._parent.nested:
            s.expire_all()
            s.begin_nested()

    yield test_session

    # Roll back the parent transaction after the test is complete
    test_session.close()
    trans.rollback()
    connection.close()


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """
    Create a test database and use it for the whole test session.
    """

    test_db_url = get_test_db_url()

    # Create the test database
    if not database_exists(test_db_url):
        create_database(test_db_url)
    test_engine = create_engine(test_db_url)
    Base.metadata.create_all(test_engine)

    # Run the tests
    yield

    # Drop the test database
    drop_database(test_db_url)


@pytest.fixture
def client(test_db):
    """
    Get a TestClient instance that reads/write to the test database.
    """

    def get_test_db():
        yield test_db

    app.dependency_overrides[get_db] = get_test_db

    yield TestClient(app)


@pytest.fixture
def test_password() -> str:
    return "securepassword"


def get_password_hash() -> str:
    """
    Password hashing can be expensive so a mock will be much faster
    """
    return "password"


@pytest.fixture
def test_superuser(test_db: Session) -> models.Admins:
    """
    Superuser for testing
    """

    user = models.User(
        firstname='Shift2Go',
        lastname='Admin',
        email='admin@shift2go.com',
        is_active=True,
        userType=constants.ADMIN,
        hashed_password=get_password_hash(),
        is_superuser=True,
        is_verified=True,
        phone='233504359666',
        address='Accra, Ghana'
    )
    test_db.add(user)
    test_db.commit()

    admin = models.Admins(
        userID=user.id
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)

    return admin


@pytest.fixture
def test_contractor(test_db: Session) -> models.Contractors:
    """
    Superuser for testing
    """

    user = models.User(
        firstname='Contractor',
        lastname='Shift2Go',
        email='contractor@shift2go.com',
        is_active=True,
        userType=constants.CONTRACTOR,
        hashed_password=get_password_hash(),
        is_superuser=False,
        is_verified=True,
        phone='233504359666',
        address='Accra, Ghana'
    )
    test_db.add(user)
    test_db.commit()


    # create Contractor
    contractor = models.Contractors(
        userID=user.id,
        profilePicture='www.google.com',
        jobRoles=None,
        verified=True
    )
    test_db.add(contractor)
    test_db.commit()
    test_db.refresh(contractor)

    # create notification
    notification = models.NotificationSettings(
        email=True,
        push=True,
        createdBy=user.id
    )
    test_db.add(notification)
    test_db.commit()
    test_db.refresh(notification)

    return contractor


@pytest.fixture
def test_unverified_contractor(test_db: Session) -> models.Contractors:
    """
    Superuser for testing
    """

    user = models.User(
        firstname='Unverified Contractor',
        lastname='Shift2Go',
        email='unverified_contractor@shift2go.com',
        is_active=True,
        userType=constants.CONTRACTOR,
        hashed_password=get_password_hash(),
        is_superuser=False,
        is_verified=True,
        phone='233504359666',
        address='Accra, Ghana'
    )
    test_db.add(user)
    test_db.commit()


    # create Contractor
    contractor = models.Contractors(
        userID=user.id,
        profilePicture='www.google.com',
        jobRoles=None,
        verified=False
    )
    test_db.add(contractor)
    test_db.commit()
    test_db.refresh(contractor)

    # create notification
    notification = models.NotificationSettings(
        email=True,
        push=True,
        createdBy=user.id
    )
    test_db.add(notification)
    test_db.commit()
    test_db.refresh(notification)

    return contractor


@pytest.fixture
def test_manager(test_db: Session) -> models.HotelAdmins:
    """
    Superuser for testing
    """

    user = models.User(
        firstname='Manager',
        lastname='Shift2Go',
        email='manger@shift2go.com',
        is_active=True,
        userType=constants.MANAGER,
        hashed_password=get_password_hash(),
        is_superuser=False,
        is_verified=True,
        phone='233504359666',
        address='Accra, Ghana'
    )
    test_db.add(user)
    test_db.commit()

    # create Manager
    manager = models.HotelAdmins(
        userID=user.id,
        profilePicture='www.google.com'
    )
    test_db.add(manager)
    test_db.commit()
    test_db.refresh(manager)

    return manager


def verify_password_mock(first: str, second: str) -> bool:
    return True


@pytest.fixture
def contractor_token_headers(
    client: TestClient, test_contractor: models.Contractors, test_db: Session, test_password, monkeypatch
) -> t.Dict[str, str]:
    monkeypatch.setattr(security, "verify_password", verify_password_mock)

    user = crud.get_user_by_id(test_db, test_contractor.userID)
    login_data = {
        "username": user.email,
        "password": test_password,
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers


@pytest.fixture
def manager_token_headers(
    client: TestClient, test_manager: models.HotelAdmins, test_db: Session, test_password, monkeypatch
) -> t.Dict[str, str]:
    monkeypatch.setattr(security, "verify_password", verify_password_mock)

    user = crud.get_user_by_id(test_db, test_manager.userID)
    login_data = {
        "username": user.email,
        "password": test_password,
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers


@pytest.fixture
def superuser_token_headers(
    client: TestClient, test_superuser: models.Admins, test_password, monkeypatch, test_db: Session
) -> t.Dict[str, str]:
    monkeypatch.setattr(security, "verify_password", verify_password_mock)

    user = crud.get_user_by_id(test_db, test_superuser.userID)
    login_data = {
        "username": user.email,
        "password": test_password,
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers


@pytest.fixture
def superuser_id(
    client: TestClient, test_superuser: models.Admins, test_password, monkeypatch, test_db: Session
) -> t.Dict[str, str]:
    monkeypatch.setattr(security, "verify_password", verify_password_mock)

    user = crud.get_user_by_id(test_db, test_superuser.userID)
    login_data = {
        "username": user.email,
        "password": test_password,
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    data = r.json()
    return data["user"]['id']

@pytest.fixture
def test_contractor_bank(test_db: Session, test_contractor: models.Contractors) -> models.BankInformations:
        # add bank information
    bank = models.BankInformations(
        name='First National Bank',
        routingNumber='0123456789',
        accountNumber='9876543210',
        createdBy=test_contractor.userID
    )
    test_db.add(bank)
    test_db.commit()
    test_db.refresh(bank)



@pytest.fixture
def test_manager_bank(test_db: Session, test_manager: models.HotelAdmins) -> models.BankInformations:
    # get user
    user = crud.get_user_by_id(test_db, test_manager.userID)
    # add hotel
    bank = models.BankInformations(
        name='Barclays',
        routingNumber='123456',
        accountNumber='123456789',
        createdBy=user.id
    )
    test_db.add(bank)
    test_db.commit()
    test_db.refresh(bank)
    return bank


@pytest.fixture
def test_manager_hotel(test_db: Session, test_manager: models.HotelAdmins, test_manager_bank: models.BankInformations) -> models.Hotels:
    # add hotel
    hotel = models.Hotels(
        name='Eusbert Hotel',
        phone='123456789',
        address='New York',
        createdBy=test_manager.userID,
        hotelAdmin=test_manager.id,
        employerIdentificationNumber='123456',
        bank_id=test_manager_bank.id,
        pictures=[],
        notification={
            'email': True,
            'push': True
        }
    )
    test_db.add(hotel)
    test_db.commit()
    test_db.refresh(hotel)
    return hotel


@pytest.fixture
def test_admin_role(test_db: Session, test_superuser: models.Admins) -> models.JobRoles:
    # add role
    role = models.JobRoles(
        name='Front Desk',
        image='www.facebook',
        createdBy=test_superuser.userID
    )
    test_db.add(role)
    test_db.commit()
    test_db.refresh(role)
    return role


@pytest.fixture
def test_manager_shift(
    test_db: Session,
    test_manager: models.HotelAdmins,
    test_manager_hotel: models.Hotels,
    test_admin_role: models.JobRoles,
) -> models.Shifts:

    shift = models.Shifts(
        name='Receptionist',
        hotel_id=test_manager_hotel.id,
        roles_ids=[test_admin_role.id],
        pay=150,
        startTime=datetime.now() + timedelta(hours=1),
        endTime=datetime.now() + timedelta(hours=4),
        instructions='Come Early',
        audienceType='MARKET',
        createdBy=test_manager.userID,
        # contractor_id=test_contractor.id
    )    
    test_db.add(shift)
    test_db.commit()
    test_db.refresh(shift)
    return shift
