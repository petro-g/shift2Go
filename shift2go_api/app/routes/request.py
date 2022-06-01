import typing as t

from app.config.auth import (get_current_active_contractor,
                             get_current_active_contractor_or_admin, get_current_active_manager,
                             get_current_active_user)
from app.config.utils import get_request_shift_data, process_header
from app.db import models, schemas
from app.db.crud import (create_request, delete_request, edit_request, get_request, get_requests)
from app.db.session import get_db
from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)


request_router = r = APIRouter()


@r.post(
    "s/create",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.ShiftRequestOut,
    tags=['contractor']
)
async def create_a_shift_request(
    request: schemas.ShiftRequestIn,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    request = create_request(db, current_user, request)
    get_request_shift_data(request)
    return request


@r.get(
    "s",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftRequestOut],
    tags=['contractor', 'admin', 'manager']
)
async def get_all_shift_request(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    pagination = get_requests(db, current_user, page)
    for request in pagination.data:
        get_request_shift_data(request)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/{request_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftRequestOut,
    tags=['contractor', 'admin', 'manager']
)
async def get_a_shift_request(
    request_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    requests = get_request(db, current_user, request_id)
    get_request_shift_data(requests)
    return requests


@r.patch(
    "/update/{request_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftRequestOut,
    tags=['contractor', 'admin']
)
async def update_a_shift_request(
    request: schemas.ShiftRequestEdit,
    request_id: int,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    requests = edit_request(db, current_user, request, request_id)
    get_request_shift_data(requests)
    return requests

@r.delete(
    "/delete/{request_id}",
    status_code=status.HTTP_200_OK,
    tags=['contractor', 'admin']
)
async def delete_a_shift_request(
    request_id: int,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    deleted = delete_request(db, current_user, request_id)
    return {
        "status": "success" if deleted else "failed"
    }
