#!/usr/bin/env python3

from app.db import models
from app.db.session import SessionLocal
from app.config import constants, security

def init() -> None:
    db = SessionLocal()

    hashed_password = security.get_password_hash('password')
    db_user = models.User(
        firstname='Shift2Go',
        lastname='Admin',
        email='info@kwgsoftworks.com',
        is_active=True,
        userType=constants.ADMIN,
        hashed_password=hashed_password,
        is_superuser=True,
        is_verified=True,
        phone='0123456789',
        address='US'
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
    print(db_user)


if __name__ == "__main__":
    print("Creating super_admin info@kwgsoftworks.com")
    init()
    print("Super_admin created")
