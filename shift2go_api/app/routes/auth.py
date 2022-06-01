from app.config.auth import verify_user
from datetime import timedelta

from app.config import constants, security
from app.config.auth import (authenticate_user, get_current_user,
                             password_change,
                             token_password_change, verify_and_generate_token)
from app.celery_config.tasks.email import (send_email_login_email, send_email_verification,
                                           send_password_reset)
from app.config.security import decode_verify_token
from app.config.utils import (generate_email_login_token,
                              generate_password_change_token,
                              generate_verification_token)
from app.db import schemas
from app.db.crud import get_user_by_email, logout_user, user_is_logged_out
from app.db.session import get_db
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Response, status)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

auth_router = r = APIRouter()


@r.post(
    "/login",
    tags=['admin', 'manager', 'contractor'],
    response_model=schemas.Token, status_code=status.HTTP_200_OK)
async def login(
    db=Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """Log into the system"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    if user.is_superuser:
        permissions = "admin"
    else:
        permissions = "user"
    access_token = security.create_access_token(
        data={"email": user.email, "id": user.id, "permissions": permissions},
        expires_delta=access_token_expires,
    )
    token = schemas.Token(access_token=access_token,
                          token_type="bearer", user=user)

    return token


@r.get(
    '/logout',
    tags=['admin', 'manager', 'contractor'],
)
async def logout(
    token: str = Depends(security.oauth2_scheme),
    db=Depends(get_db)
):
    """Log out of system"""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Has to login first",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logout_user(db, token)
    headers = {"Authorization": ""}
    return JSONResponse(content={"status": "success"}, headers=headers)


@r.get(
    "/verification",
    response_model=schemas.Token,
    tags=['admin', 'manager', 'contractor'],
    status_code=status.HTTP_200_OK
)
async def verify_account(
    token: str,
    db=Depends(get_db)
):
    """Verify you account"""
    exception = HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        detail="Invalid Token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if user_is_logged_out(db, token):
        raise exception

    payload = decode_verify_token(token)
    if not payload.get('type') == constants.EMAIL_VERIFICATION_TYPE:
        raise exception
        
    logout_user(db, token)
    verified_user = verify_user(
        db, payload.get('email'), payload.get('user_id'))
    # return verified_user

    access_token_expires = timedelta(
        minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    if verified_user.is_superuser:
        permissions = "admin"
    else:
        permissions = "user"
    access_token = security.create_access_token(
        data={"email": verified_user.email, "id": verified_user.id, "permissions": permissions},
        expires_delta=access_token_expires,
    )
    token = schemas.Token(access_token=access_token,
                          token_type="bearer", user=verified_user)

    return token


@r.post(
    "/verification/request",
    tags=['admin', 'manager', 'contractor'],
    status_code=status.HTTP_200_OK
)
async def request_verification(
    request: schemas.RequestVerification,
    background_task: BackgroundTasks,
    db=Depends(get_db)
):
    """Request account verification"""
    user = get_user_by_email(db, request.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Already verified",
            headers={"WWW-Authenticate": "Bearer"},
        )
    send_email_verification(
        user.id,
        generate_verification_token(user.id, user.email)
    )
    # background_task.add_task(
    #     send_email_verification,
    #     user.id,
    #     generate_verification_token(user.id, user.email)
    # )
    return {"status": "success", "message": "If email is registered you'll be sent a verification link"}


@r.post(
    "/password/reset",
    tags=['admin', 'manager', 'contractor'],
    status_code=status.HTTP_200_OK
)
async def reset_password(
    request: schemas.PasswordReset,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Reset your password"""
    user = get_user_by_email(db, request.email)
    if user:
        token = generate_password_change_token(user)
        id = user.id
        send_password_reset(id, token)
        # background_tasks.add_task(send_password_reset, id, token)

    return {"status": "success", "message": "If email is registered you'll be sent a password reset link"}


# @r.get(
#     "/password/reset/confirm",
#     tags=['admin', 'manager', 'contractor'],
#     status_code=status.HTTP_200_OK
# )
# async def confirm_password_reset(
#     token: str,
#     db=Depends(get_db)
# ):
#     """Confirm your password reset process"""
#     payload = decode_verify_token(token)
#     if not payload.get('type') == constants.PASSWORD_CONFIRM_TYPE:
#         raise HTTPException(
#             status_code=status.HTTP_406_NOT_ACCEPTABLE,
#             detail="Invalid Token",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     verified_user = get_user_by_email(db, payload.get('email'))
#     access_token = generate_password_change_token(verified_user)
#     token = schemas.Token(access_token=access_token, token_type="bearer")
#     return {
#         "status": "success",
#         "message": "Change password with token at /api/v1/auth/password/change as a PATCH request",
#         "token": token.access_token
#     }


@r.post(
    "/password/change",
    response_model=schemas.Token,
    tags=['admin', 'manager', 'contractor'],
    status_code=status.HTTP_202_ACCEPTED
)
async def change_password(
    response: Response,
    request: schemas.PasswordChange,
    db=Depends(get_db),
    token: str = Depends(security.oauth2_scheme),
    current_user=Depends(get_current_user)
):
    """Change your password"""
    if not current_user.email == request.email and not current_user.id == request.user_id:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Not Allowed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authenticate_user(db, request.email, request.old_password):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Wrong email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    new_token = password_change(db, request)
    logout_user(db, token)
    response.headers['Authorization'] = f'Bearer {new_token.access_token}'
    return new_token


@r.patch(
    "/password/change",
    tags=['admin', 'manager', 'contractor'],
    response_model=schemas.Token,
    status_code=status.HTTP_202_ACCEPTED
)
async def change_password(
    response: Response,
    request: schemas.TokenPasswordChange,
    db=Depends(get_db),
):
    """Change your password with token from password reset email"""
    exception = HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        detail="Invalid Token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_verify_token(request.token)
    if not payload.get('type') == constants.PASSWORD_CHANGE_TYPE:
        raise exception
    verified_user = get_user_by_email(db, payload.get('email'))
    if not verified_user:
        raise exception

    new_token = token_password_change(
        db, email=payload.get('email'), password=request.new_password)
    response.headers['Authorization'] = f'Bearer {new_token.access_token}'
    return new_token


@r.get(
    "/token_login",
    tags=['contractor'],
    response_model=schemas.Token,
    status_code=status.HTTP_202_ACCEPTED
)
async def login_with_token(
    response: Response,
    token: str,
    db=Depends(get_db),
):
    """Login with token"""
    exception = HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        detail="Invalid Token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_verify_token(token)
    if not payload.get('type') == constants.EMAIL_LOGIN_TOKEN_TYPE:
        raise exception

    if user_is_logged_out(db, token):
        raise exception

    new_token = verify_and_generate_token(db, payload.get('email'))

    logout_user(db, token)
    response.headers['Authorization'] = f'Bearer {new_token.access_token}'
    return new_token


@r.post(
    "/email_login",
    tags=['admin', 'contractor', 'manager']
)
async def login_with_email(
    email: str,
    background_task: BackgroundTasks,
    db=Depends(get_db),
):
    """Receive a login email"""
    user = get_user_by_email(db, email)
    if user:
        send_email_login_email(
            user.id,
            generate_email_login_token(user)
        )
        # background_task.add_task(
        #     send_email_login_email,
        #     user.id,
        #     generate_email_login_token(user)
        # )

    return {"status": "success", "message": "If email is registered you'll be sent a login link"}
