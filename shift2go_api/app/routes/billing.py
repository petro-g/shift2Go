import typing as t

from app.config.auth import get_current_active_user, get_current_active_superuser
from app.config.utils import get_bill_data, process_header
from app.db import schemas
from app.db.crud import (delete_bill, edit_billing, get_bill, get_hotel_bills,
                         get_bills, create_bill)
from app.db.session import get_db
from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)
from datetime import date


billing_router = r = APIRouter()


@r.post(
    "/create",
    tags=['admin'],
    response_model=schemas.BillingOut,
    status_code=status.HTTP_201_CREATED
)
async def create_a_bill(
    request: schemas.BillingIn,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    bill = create_bill(db, current_user, request)
    get_bill_data(bill)
    return bill


@r.get(
    "s",
    tags=['admin', 'manager', 'contractor'],
    response_model=t.List[schemas.BillingOut],
    status_code=status.HTTP_200_OK
)
async def get_all_billings(
    response: Response,
    start_date: date = None,
    end_date: date = None,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """
    the date should have ISO 8601 format
    2021-11-19
    """
    pagination = get_bills(db, current_user, page, start_date, end_date)
    for bill in pagination.data:
        get_bill_data(bill)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "s/hotel/{hotel_id}",
    tags=['admin'],
    response_model=t.List[schemas.BillingOut],
    status_code=status.HTTP_200_OK
)
async def get_all_hotel_billings(
    response: Response,
    hotel_id: int,
    start_date: date = None,
    end_date: date = None,
    page: int = 1,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """
    the date should have ISO 8601 format
    2021-11-19
    """
    pagination = get_hotel_bills(
        db, current_user, page, start_date, end_date, hotel_id)
    for bill in pagination.data:
        get_bill_data(bill)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/{billing_id}",
    tags=['admin', 'manager', 'contractor'],
    response_model=schemas.BillingOut,
    status_code=status.HTTP_200_OK
)
async def get_a_billing(
    billing_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    bill = get_bill(db, current_user, billing_id)
    get_bill_data(bill)
    return bill


@r.patch(
    "/update/{billing_id}",
    response_model=schemas.BillingOut,
    tags=['admin', 'manager', 'contractor'],
    status_code=status.HTTP_201_CREATED
)
async def update_a_billing(
    billing_id: int,
    request: schemas.BillingEdit,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    bill = edit_billing(db, current_user, request, billing_id)
    get_bill_data(bill)
    return bill


@r.delete(
    "/delete/{billing_id}",
    status_code=status.HTTP_200_OK,
    tags=['admin', 'manager', 'contractor'],
)
async def delete_a_billing(
    billing_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    deleted = delete_bill(db, current_user, billing_id)
    return {
        "status": "success" if deleted else "failed"
    }
