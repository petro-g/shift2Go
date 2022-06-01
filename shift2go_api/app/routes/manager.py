import typing as t

from app.config.auth import (get_current_active_manager, generate_login_token,
                             get_current_active_superuser)
from app.config.utils import get_manager_data, process_header, get_module_logger
from app.db import schemas
from app.db.crud import (get_manager_by_user_id, get_managers, register_manager, delete_manager)
from app.db.session import get_db
from fastapi import (APIRouter, BackgroundTasks, Depends, Response,
                     status, HTTPException)

from app.config.utils import generate_verification_token
from app.celery_config.tasks.email import send_email_verification


manager_router = r = APIRouter()
logger = get_module_logger(__name__)


@r.post(
    '/signup',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.HotelAdminToken,
    tags=['manager']
)
async def signup_hotel_admin(
    request: schemas.HotelAdminRegister,
    response: Response,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    # Create manager CRUD call
    manager = register_manager(db, request)
    get_manager_data(manager)
    db_user = manager.owner
    send_email_verification(
        db_user.id,
        generate_verification_token(db_user.id, db_user.email)
    )
    token = generate_login_token(manager.owner)
    # background_tasks.add_task(db_user.id, generate_verification_token(db_user.id, db_user.email))
    response.headers['Authorization'] = f'Bearer {token}'

    logger.info("sign up created for user: %s", db_user.id)
    return {
        'manager': manager,
        'access_token': token
    }


@r.get(
    "s",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.HotelAdminOut],
    tags=['admin']
)
async def all_managers(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    pagination = get_managers(db, page)
    for manager in pagination.data:
        get_manager_data(manager)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=schemas.HotelAdminOut,
    tags=['manager']
)
async def get_manager_account(
    current_user=Depends(get_current_active_manager),
    db=Depends(get_db)
):
    manager = get_manager_by_user_id(db, current_user.id)
    get_manager_data(manager, show_token=True)
    return manager


@r.delete(
    "/delete/{manager_id}",
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def delete_manager_account(
    manager_id: int,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    deleted = delete_manager(db, manager_id)
    return {
        "status": "success" if deleted else "failed"
    }
