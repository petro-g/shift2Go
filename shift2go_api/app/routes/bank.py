import typing as t

from app.config import constants
from app.config.auth import (get_current_active_contractor,
                             get_current_admin_or_manager,
                             get_current_active_superuser,
                             get_current_active_user)
from app.config.utils import get_owner, process_header
from app.db import schemas
from app.db.crud import (create_bank, edit_my_bank,
                         get_bank, get_bank_no_catch, get_banks, delete_bank)
from app.db.session import get_db
from fastapi import APIRouter, Depends, Response, status
from fastapi.exceptions import HTTPException

bank_router = r = APIRouter()


@r.post(
    "/add",
    response_model=schemas.BankOut,
    status_code=status.HTTP_201_CREATED,
    tags=['admin', 'contractor']
)
async def add_bank(
    request: schemas.BankIn,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    Add Bank Information
    """
    if current_user.userType == constants.CONTRACTOR:
        if get_bank_no_catch(db, current_user):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='you already own a bank account')
    bank = create_bank(db, current_user, request)
    get_owner(bank)  # owner
    return bank


@r.get(
    "s",
    response_model=t.List[schemas.BankOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'manager']
)
async def bank_informations(
    response: Response,
    page: int = 1,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_or_manager)
):
    """
    Admin: Get All System Bank Information
    Contractor: Get All Bank Information owned by Contractor
    Hotel Manager: Get All Bank Information owned Manager
    """
    pagination = get_banks(db, current_user, page)
    for bank in pagination.data:
        get_owner(bank)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/me",
    response_model=schemas.BankOut,
    status_code=status.HTTP_200_OK,
    tags=['contractor']
)
async def get_my_bank_information(
    db=Depends(get_db),
    current_user=Depends(get_current_active_contractor)
):
    """
    Admin: Get a Bank Information
    Contractor: Get a Bank Information owned by Contractor
    Hotel Manager: Get a Bank Information owned by Manager
    """

    bank = get_bank(db, current_user)
    get_owner(bank)
    return bank


@r.get(
    "/{bank_id}",
    response_model=schemas.BankOut,
    status_code=status.HTTP_200_OK,
    tags=['admin', 'manager']
)
async def get_bank_information(
    bank_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_or_manager)
):
    """
    Admin: Get a Bank Information
    Hotel Manager: Get a Bank Information owned by Manager
    """
    bank = get_bank(db, current_user, bank_id)
    get_owner(bank)
    return bank


@r.patch(
    "/update/me",
    response_model=schemas.BankOut,
    status_code=status.HTTP_201_CREATED,
    tags=['admin', 'contractor', 'manager']
)
async def update_bank_information(
    bank_id: int,
    request: schemas.BankEdit,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    Admin: Update a Bank Information
    Contractor: Update a Bank Information owned by Contractor
    Hotel Manager: Update a Bank Information owned Manager
    """
    bank = edit_my_bank(db, current_user, request, bank_id)
    get_owner(bank)
    return bank


@r.delete(
    "/delete/{bank_id}",
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def delete_bank_informations(
    bank_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Admin: Delete a Bank Information
    Contractor: Delete a Bank Information owned by Contractor
    Hotel Manager: Delete a Bank Information owned Manager
    """
    deleted = delete_bank(db, current_user, bank_id)
    return {
        "status": "success" if deleted else "failed"
    }
