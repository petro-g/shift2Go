from datetime import timedelta
import jwt
from jwt import PyJWTError

from app.db.crud import get_user_by_id
from app.config import constants, security
from app.db import models, schemas, session
from app.db.crud import create_admin, get_user_by_email, user_is_logged_out
from fastapi import Depends, HTTPException, status
from app.config.config import PROJECT_NAME


def verify_user(db, email: str, user_id: str) -> models.User:
    user = get_user_by_email(db, email)
    if not user:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            # return False  # User already exists
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Already verified")

    user.is_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def get_current_user(
    db=Depends(session.get_db),
    token: str = Depends(security.oauth2_scheme)
):
    if user_is_logged_out(db, token):
        raise HTTPException(
            status_code=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED,
            detail="Login required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        permissions: str = payload.get("permissions")
        token_data = schemas.TokenData(email=email, permissions=permissions)
    except PyJWTError as error:
        # TODO: check if email token has expires then ask user to request again
        print(error)
        raise credentials_exception
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inactive user")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Please verify you email")
    return user


async def get_unverified_current_user(
    db=Depends(session.get_db),
    token: str = Depends(security.oauth2_scheme)
):
    if user_is_logged_out(db, token):
        raise HTTPException(
            status_code=status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED,
            detail="Login required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, security.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        permissions: str = payload.get("permissions")
        token_data = schemas.TokenData(email=email, permissions=permissions)
    except PyJWTError as error:
        # TODO: check if email token has expires then ask user to request again
        print(error)
        raise credentials_exception
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inactive user")
    # if not user.is_verified:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
    #                         detail="Please verify you email")
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inactive user")
    if not current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Please verify you email")
    return current_user


async def get_current_active_contractor_or_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.userType == constants.MANAGER:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Manager not allowed")
    return current_user


async def get_current_active_manager_or_contractor(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.userType == constants.ADMIN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Admin not allowed")
    return current_user


async def get_current_admin_or_manager(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.userType == constants.MANAGER or current_user.userType == constants.ADMIN:
        return current_user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Only Admin or Hotel Admin allowed")


async def get_unverified_current_active_manager(current_user: models.User = Depends(get_unverified_current_user)) -> models.User:
    if current_user.userType == constants.CONTRACTOR or current_user.userType == constants.ADMIN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Only Hotel manager allowed")
    return current_user

async def get_current_active_manager(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.userType == constants.CONTRACTOR or current_user.userType == constants.ADMIN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Only Hotel manager allowed")
    return current_user


async def get_current_active_contractor(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.userType == constants.MANAGER or current_user.userType == constants.ADMIN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Only Contractor allowed")
    return current_user


async def get_current_active_superuser(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Only Super user allowed"
        )
    return current_user


def authenticate_user(db, email: str, password: str) -> models.User:
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"You have been banned from {PROJECT_NAME}. Contact Admin")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Please verify you email")
    if not security.verify_password(password, user.hashed_password):
        return False
    return user


def generate_login_token(user: models.User) -> str:

    access_token_expires = timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    if user.is_superuser:
        permissions = "admin"
    else:
        permissions = "user"
    access_token = security.create_access_token(
        data={"email": user.email, "user_id": user.id,
              "permissions": permissions},
        expires_delta=access_token_expires,
    )
    token = schemas.Token(access_token=access_token, token_type="bearer")
    return token.access_token


def password_change(db, request: schemas.PasswordChange) -> schemas.Token:
    user = get_user_by_email(db, request.email)
    user.hashed_password = security.get_password_hash(request.new_password)
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token_expires = timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    if user.is_superuser:
        permissions = "admin"
    else:
        permissions = "user"
    access_token = security.create_access_token(
        data={"email": user.email, "user_id": user.id,
              "permissions": permissions},
        expires_delta=access_token_expires,
    )
    token = schemas.Token(access_token=access_token, token_type="bearer")
    return token


def verify_and_generate_token(db, email: str) -> schemas.Token:
    user = get_user_by_email(db, email)
    user.is_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token_expires = timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    permissions = "user"
    access_token = security.create_access_token(
        data={"email": user.email, "user_id": user.id,
              "permissions": permissions},
        expires_delta=access_token_expires,
    )
    token = schemas.Token(access_token=access_token, token_type="bearer")
    return token


def token_password_change(db, email: str, password: str) -> schemas.Token:
    user = get_user_by_email(db, email)
    user.hashed_password = security.get_password_hash(password)
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token_expires = timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    if user.is_superuser:
        permissions = "admin"
    else:
        permissions = "user"
    access_token = security.create_access_token(
        data={"email": user.email, "user_id": user.id,
              "permissions": permissions},
        expires_delta=access_token_expires,
    )
    token = schemas.Token(access_token=access_token, token_type="bearer")
    return token


def sign_up_new_admin(db, request: schemas.AdminRegister) -> models.Admins:
    user = get_user_by_email(db, request.email)
    if user:
        return False  # User already exists
    new_admin = create_admin(
        db,
        request
    )

    return new_admin
