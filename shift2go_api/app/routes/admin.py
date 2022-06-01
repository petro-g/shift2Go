import typing as t

from app.config.auth import (generate_login_token, get_current_active_superuser,
                             sign_up_new_admin)
from app.config.utils import (get_owner,
                              process_header, get_module_logger)
from app.db import schemas
from app.db.crud import (admin_update, get_admin_by_user_id, get_user, set_default_roles, set_default_certificate_types,
                         get_users, platform_summary, verify_user_manually, master_reset)
from app.db.session import get_db
from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status)

admin_router = r = APIRouter()
logger = get_module_logger(__name__)


@r.post(
    "/signup",
    response_model=schemas.AdminOutToken,
    status_code=status.HTTP_201_CREATED,
)
async def signup_admin(
    request: schemas.AdminRegister,
    response: Response,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """Sign up an Admin"""
    new_admin = sign_up_new_admin(db, request)
    if not new_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # try:
        # send_email_verification.apply_async(kwargs={
        #     'user_id': new_admin.owner.id,
        #     'token': generate_verification_token(new_admin.owner.id, new_admin.owner.email)
        # })
        # background_tasks.add_task(send_email_verification, new_admin.owner.id, generate_verification_token(new_admin.owner.id, new_admin.owner.email))
    # except Exception:
    #     pass
    get_owner(new_admin)
    token = generate_login_token(new_admin.owner)
    response.headers['Authorization'] = f'Bearer {token}'

    return {
        'admin': new_admin,
        'access_token': token
    }


@r.get(
    "/me",
    response_model=schemas.AdminOut
)
async def get_logged_in_user(
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Get Admin account details
    """
    admin = get_admin_by_user_id(db, current_user)
    try:
        get_owner(admin)  # get user
    except Exception as err:
        logger.error(f"Exception: {err}")
    return admin


@r.patch(
    "/update",
    response_model=schemas.AdminOut
)
async def update_admin(
    request: schemas.AdminEdit,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Update Admin account details
    """
    admin = admin_update(db, current_user, request)
    try:
        admin.owner  # get user
    except Exception as err:
        logger.error(f"Exception: {err}")
    return admin


@r.get(
    "/users",
    response_model=t.List[schemas.UserDetails],
    # response_model_exclude=['hashed_password'],
)
async def all_system_users(
    response: Response,
    page: int = 1,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    """
    Get all User accounts on system
    """
    pagination = get_users(db, page)
    process_header(response, pagination, page)

    return pagination.data


@r.post(
    "/user/verify",
    response_model=schemas.UserDetails,
)
async def verify_admin_manually(
    user_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Verify Admin manually
    """
    user = verify_user_manually(db, user_id)
    return user


@r.get(
    "/user/{user_id}",
    response_model=schemas.UserDetails,
)
async def user_details(
    request: Request,
    user_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Get any User account details
    """
    user = get_user(db, user_id)
    return user


@r.get(
    '/summary',
    response_model=schemas.Summary
)
async def summary(
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    total = platform_summary(db)
    return total


@r.get(
    '/default_roles',
    response_model=t.List[schemas.JobRolesOut]
)
async def create_default_roles(
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
   return set_default_roles(db, current_user)


@r.get(
    '/default_certificate_types',
    response_model=t.List[schemas.CertificateTypeOut]
)
async def create_default_certificate_tpe(
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    return set_default_certificate_types(db)

@r.post(
    '/clear_database',
)
async def clean_database(
    current_user=Depends(get_current_active_superuser)
):
    results = master_reset()
    return {
        'status': 'success' if results else 'failed'
    }