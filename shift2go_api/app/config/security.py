import uuid

import jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.config import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(*, data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_verify_token(data: dict):
    encoded_jwt = jwt.encode(data, SECRET_KEY)
    return encoded_jwt


def decode_verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY)
        if 'email' in payload or 'type' in payload or 'user_id' in payload:
            return payload
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as error:
        print(error)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
