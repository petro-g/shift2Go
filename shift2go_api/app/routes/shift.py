import typing as t

from app.config import constants
from app.config.auth import (get_current_active_contractor,
                             get_current_active_contractor_or_admin,
                             get_current_active_manager,
                             get_current_active_manager_or_contractor,
                             get_current_active_user,
                             get_current_admin_or_manager)
from app.config.utils import get_owner, get_shift_data, process_header, get_module_logger
from app.db import schemas
from app.db.crud import (accept_shift, accepted_shifts, add_shift,
                         all_awarded_shifts, award_a_shift, contractor_ongoing_shift,
                         contractor_shift_history, contractor_upcoming_shift,
                         decline_shift, delete_shift, edit_shift, end_shift,
                         get_shift, get_shifts, start_shift, hotel_ongoing_shift,
                         confirm_shift, confirmed_shifts, get_hotel_shifts)
from app.db.session import get_db
from fastapi import APIRouter, Depends, Response, status
from datetime import datetime, date

shift_router = r = APIRouter()
logger = get_module_logger(__name__)

@r.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.ShiftOut,
    tags=['manager']
)
async def create_shift(
    request: schemas.ShiftIn,
    db=Depends(get_db),
    current_user=Depends(get_current_active_manager)
):
    """
    Create a shift
    """
    shift = add_shift(db, current_user, request)
    get_shift_data(shift)
    return shift


@r.get(
    "s",
    status_code=status.HTTP_200_OK,
    # response_model=t.List[schemas.ShiftOut],
    tags=['manager', 'admin', 'contractor']
)
async def get_all_shifts(
    response: Response,
    page: int = 1,
    audience: str = None,
    job_role_id: int = None,
    date: date = None,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    Params: 
        audience
            type
                MARKET, FAVOURITE, MANUAL (Strings)

                MARKET: you get all the shifts whose audienceType is MARKET

                FAVOURITE: you get all the shifts from hotels which have you as favourite and the shifts targetAudience have your contractor id

        job_role_id:
            type
                id of a job role

        date:
            the date should have ISO 8601 format 
            2021-11-19
    """
    audience_type = None
    if audience is not None:
        try:
            audience_type = audience.upper()
        except Exception as err:
            logger.error(f"Exception: {err}")

    pagination = get_shifts(
        db=db, user=current_user, audience=audience_type, page=page, role_id=job_role_id, date=date)

    for shift in pagination.data:
        get_shift_data(shift, show_user=current_user.userType ==
                       constants.MANAGER)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "s/hotel",
    status_code=status.HTTP_200_OK,
    # response_model=t.List[schemas.ShiftOut],
    tags=['manager', 'admin', 'contractor']
)
async def get_all_shifts(
        response: Response,
        hotel_id: int,
        page: int = 1,
        audience: str = None,
        job_role_id: int = None,
        date: date = None,
        db=Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    """
    Params:
        audience
            type
                MARKET, FAVOURITE, MANUAL (Strings)
                MARKET: you get all the shifts whose audienceType is MARKET
                FAVOURITE: you get all the shifts from hotels which have you as favourite and the shifts targetAudience have your contractor id
        job_role_id:
            type
                id of a job role
        date:
            the date should have ISO 8601 format
            2021-11-19
    """
    audience_type = None
    if audience is not None:
        try:
            audience_type = audience.upper()
        except Exception:
            pass

    pagination = get_hotel_shifts(
        db=db, user=current_user, hotel_id=hotel_id, audience=audience_type, page=page, role_id=job_role_id, date=date)

    for shift in pagination.data:
        get_shift_data(shift, show_user=current_user.userType ==
                                        constants.MANAGER)
    process_header(response, pagination, page)
    return pagination.data



@r.patch(
    "/update/{shift_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['manager', 'admin']
)
async def update_shift(
    shift_id: int,
    request: schemas.ShiftEdit,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    Update a shift by id
    """
    shift = edit_shift(db, current_user, request, shift_id)
    get_shift_data(shift)
    return shift


@r.delete(
    "/delete/{shift_id}",
    status_code=status.HTTP_200_OK,
    tags=['manager', 'admin']
)
async def delete_a_shift(
    shift_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_or_manager)
):
    """
    Delete by Shift by id
    """
    deleted = delete_shift(db, current_user, shift_id)
    return {
        "status": "success" if deleted else "failed"
    }


@r.patch(
    "/clock_in",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['contractor']
)
async def start_a_shift(
    request: schemas.ClockIn,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    """
    Start a shift
    """
    shift = start_shift(db, current_user, request)
    get_shift_data(shift)
    return shift


@r.post(
    "/clock_out",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['contractor']
)
async def end_a_shift(
    request: schemas.ClockOut,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    """
    End a shift
    """
    shift = end_shift(db, current_user, request)
    get_shift_data(shift)
    return shift


@r.post(
    "/award",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['admin', 'manager']
)
async def award_shift(
    request: schemas.AwardShift,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Award a shift to a contractor. Attaches contractor id to Shift
    """
    shift = award_a_shift(db, current_user, request)
    get_shift_data(shift)
    return shift


@r.get(
    "/awarded",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftOut],
    tags=['contractor']
)
async def awarded_shifts(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    """
    Get all shift assigned to Contractor which is still pending. Shift status is PENDING
    """
    pagination = all_awarded_shifts(db, current_user, page)
    for shift in pagination.data:
        get_shift_data(shift)
    process_header(response, pagination, page)
    return pagination.data


@r.patch(
    "/accept",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['contractor']
)
async def accept_a_shift(
    shift_id: int,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    """
    Accept a Shift assigned to a Contractor. Changes Shift status to ACCEPTED
    """
    shift = accept_shift(db, current_user, shift_id)
    get_shift_data(shift)
    return shift


@r.patch(
    "/decline",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['contractor']
)
async def decline_a_shift(
    shift_id: int,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    """
    Decline a Shift assigned to contractor. Changes Shift status to PENDING and removes contractor_id from shift
    """
    shift = decline_shift(db, current_user, shift_id)
    get_shift_data(shift)
    return shift


@r.patch(
    "/accepted",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftOut],
    tags=['contractor']
)
async def all_accepted_shifts(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    """
    Gets all shifts accepted to contractor
    """
    pagination = accepted_shifts(db, current_user, page)
    for accept in pagination.data:
        get_shift_data(accept, show_user=True)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/upcoming",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftOut],
    tags=['admin', 'contractor']
)
async def upcoming_shift(
    response: Response,
    contractor_id: int = None,
    page: int = 1,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    """
    Gets all shift assigned to contractor and accepted but has not started
    """
    pagination = contractor_upcoming_shift(
        db, current_user, page, contractor_id)
    for accept in pagination.data:
        get_shift_data(accept, show_user=True)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/contractor/ongoing",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftOut],
    tags=['admin', 'contractor']
)
async def contractors_ongoing_shift(
    contractor_id: int = None,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    """
    Gets all shift assigned to contractor and has started
    """
    shifts = contractor_ongoing_shift(
        db, current_user, contractor_id)
    for shift in shifts:
        get_shift_data(shift)
    return shifts


@r.get(
    "/hotel/ongoing",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftOut],
    tags=['admin', 'manager']
)
async def hotels_ongoing_shift(
    hotel_id: int,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Gets all shift assigned to contractor and has started
    """
    shifts = hotel_ongoing_shift(
        db, current_user, hotel_id)
    for shift in shifts:
        get_shift_data(shift)
    return shifts


@r.get(
    "/history",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftOut],
    tags=['admin', 'contractor']
)
async def shift_history(
    response: Response,
    contractor_id: int = None,
    page: int = 1,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    """
    Get all shift history of contractor
    Includes cancelled shifts
    """
    pagination = contractor_shift_history(
        db, current_user, page, contractor_id)
    for accept in pagination.data:
        get_shift_data(accept)
    process_header(response, pagination, page)
    return pagination.data


@r.post(
    "/confirm",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['admin', 'manager']
)
async def confirm_shift_completion(
    shift_id: int,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Confirm shifts completed by Contractor
    """

    shift = confirm_shift(db, current_user, shift_id)
    get_shift_data(shift)
    return shift


@r.post(
    "/confirmed",
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ShiftOut],
    tags=['admin', 'manager']
)
async def confirmed_shift_completion(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Get all Shifts whose completion has been confirmed
    """

    pagination = confirmed_shifts(db, current_user, page)
    for shift in pagination.data:
        get_shift_data(shift)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/{shift_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ShiftOut,
    tags=['manager', 'admin', 'contractor']
)
async def get_a_shift(
    shift_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    Get a Shift by id
    """
    shift = get_shift(db, current_user, shift_id)
    get_shift_data(shift)
    return shift

    