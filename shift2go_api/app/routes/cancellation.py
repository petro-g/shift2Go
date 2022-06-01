import typing as t

from app.config import security
from app.config.auth import (get_current_active_contractor,
                             get_current_active_contractor_or_admin,
                             get_current_active_user)
from app.celery_config.tasks.utils import shift_cancellation
from app.config.utils import get_cancelled_shift_data, process_header
from app.db import schemas
from app.db.crud import (cancel_shift, edit_cancellation, get_cancellation,
                         get_cancellation_status, get_cancellations)
from app.db.session import get_db
from fastapi import (APIRouter, BackgroundTasks, Depends, Response, status)

cancelled_router = r = APIRouter()


@r.post(
    "/create",
    response_model=schemas.CancellationOut,
    status_code=status.HTTP_201_CREATED,
    tags=['admin', 'contractor']
)
async def cancell_a_shift(
    request: schemas.CancellationIn,
    background_task: BackgroundTasks,
    token: str = Depends(security.oauth2_scheme),
    db=Depends(get_db),
    current_user=Depends(get_current_active_contractor_or_admin)
):
    """
    Add a new Cancellation
    """
    cancellation = cancel_shift(db, current_user, request)
    get_cancelled_shift_data(cancellation)
    shift_cancellation.apply_async(kwargs={
        'user_id': current_user.id,
        'token': token
    })
    # background_task.add_task(shift_cancellation, current_user.id, token)
    return cancellation


@r.get(
    "s",
    response_model=t.List[schemas.CancellationOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def get_all_cancellation(
    response: Response,
    page: int = 1,
    user_id: int = None,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View all Cancellations on System
    """
    pagination = get_cancellations(db, current_user, page, user_id)
    for cancellation in pagination.data:
        get_cancelled_shift_data(cancellation)
    process_header(response, pagination, page)
    return pagination.data


@r.patch(
    "/update/{cancellation_id}",
    response_model=schemas.CancellationOut,
    status_code=status.HTTP_201_CREATED,
    tags=['admin', 'contractor']
)
async def update_cancellation_information(
    cancellation_id: int,
    request: schemas.CancellationEdit,
    db=Depends(get_db),
    current_user=Depends(get_current_active_contractor_or_admin)
):
    """
    Update a Cancellation
    """
    cancellation = edit_cancellation(
        db, current_user,  request, cancellation_id)
    get_cancelled_shift_data(cancellation)
    return cancellation


@r.get(
    '/pre_cancellation',
    status_code=status.HTTP_200_OK,
    response_model=schemas.Penalty,
    tags=['contractor']
)
async def cancellation_status(
    shift_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_contractor)
):
    return get_cancellation_status(db, current_user, shift_id)


@r.get(
    "/{cancellation_id}",
    response_model=schemas.CancellationOut,
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def get_a_cancellation(
    cancellation_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View a single Cancellation
    """
    cancellation = get_cancellation(db, current_user, cancellation_id)
    get_cancelled_shift_data(cancellation)
    return cancellation
