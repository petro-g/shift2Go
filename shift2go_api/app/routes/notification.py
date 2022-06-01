import typing as t

from app.config.auth import (get_current_active_manager_or_contractor,
                             get_current_active_user,
                             get_current_admin_or_manager)
from app.celery_config.tasks.notification import send_notification_to_multiple_users
from app.config.utils import get_notification_data, get_owner, process_header
from app.db import schemas
from app.db.crud import (get_notification, get_notification_setting, get_notifications, read_notification,
                         update_notification_setting, update_remainder_hours, create_notification)
from app.db.session import get_db
from fastapi import (APIRouter, BackgroundTasks, Depends, Response, status)

notification_router = r = APIRouter()

@r.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.NotificationOut,
    tags=['admin', 'manager']
)
async def create_a_notification(
    request: schemas.NotificationIn,
    background_task: BackgroundTasks,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    notification = create_notification(db, current_user, request)
    get_notification_data(notification)
    send_notification_to_multiple_users(notification)
    return notification


@r.get(
    "s",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.NotificationOut],
    tags=['admin', 'contractor', 'manager']
)
async def get_all_notifications(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    pagination = get_notifications(db, current_user, page)
    for notification in pagination.data:
        get_notification_data(notification)
    process_header(response, pagination, page)
    return pagination.data


@r.post(
    "/settings/me",
    status_code=status.HTTP_200_OK,
    response_model=schemas.NotificationSettingsOut,
    tags=['contractor', 'manager']
)
async def notification_settings(
    current_user=Depends(get_current_active_manager_or_contractor),
    db=Depends(get_db)
):
    settings = get_notification_setting(db, current_user)
    get_owner(settings)
    return settings


@r.patch(
    "/settings/update",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.NotificationSettingsOut,
    tags=['contractor', 'manager']
)
async def update_notification_settings(
    request: schemas.NotificationSettingsEdit,
    current_user=Depends(get_current_active_manager_or_contractor),
    db=Depends(get_db)
):
    settings = update_notification_setting(db, current_user, request)
    get_owner(settings)
    return settings


@r.post(
    "/reminder",
    status_code=status.HTTP_200_OK,
    response_model=schemas.NotificationSettingsOut,
    tags=['manager', 'contractor']
)
async def set_shift_reminder(
    request: schemas.Hours,
    current_user=Depends(get_current_active_manager_or_contractor),
    db=Depends(get_db)
):
    """
    Set when to send Shift reminder before shift starts
    """
    settings = update_remainder_hours(db, current_user, request)
    get_owner(settings)
    return settings


@r.patch(
    "/read",
    status_code=status.HTTP_200_OK,
    response_model=schemas.NotificationOut,
    tags=['admin', 'manager', 'contractor']
)
async def mark_notification_as_read(
    notification_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """
    Mark notification as read
    Adds user id to notification.readBy
    """
    settings = read_notification(db, current_user, notification_id)
    return settings


@r.get(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    # response_model=t.List[schemas.NotificationOut],
    tags=['admin', 'contractor', 'manager']
)
async def get_a_notification(
    notification_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    notification = get_notification(db, current_user, notification_id)
    get_notification_data(notification)
    return notification
