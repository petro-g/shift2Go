import typing as t

from app.config.auth import get_current_active_superuser
from app.config.utils import get_contractor_data, get_owner, process_header, get_module_logger
from app.db import schemas
from app.db.crud import (contractor_verify, delete_unverify_contractor,
                         get_contractor, get_contractor_by_id,
                         get_single_unverified_contractor,
                         get_unverified_contractors, unverify_contractor,
                         update_contractor)
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Response, status

unverified_contractor_router = r = APIRouter()
logger = get_module_logger(__name__)


@r.get(
    "s",
    response_model=t.List[schemas.ContractorOut],
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def unverified_contractors_informations(
    response: Response,
    page: int = 1,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    pagination = get_unverified_contractors(db, page)
    for contractor in pagination.data:
        get_contractor_data(contractor)
    process_header(response, pagination, page)
    return pagination.data


@r.patch(
    "/update",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_201_CREATED,
    tags=['admin']
)
async def update_unverified_contractor_information(
    contractor_id: int,
    request: schemas.ContractorEdit,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    contractor = get_contractor_by_id(db, contractor_id)
    if contractor.verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not allowed by verified Contracotrs'
        )
    contractor = update_contractor(db, current_user, request, contractor_id)
    get_owner(contractor)
    return contractor


@r.delete(
    "/delete/{contractor_id}",
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def delete_unverified_contractor(
    contractor_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    deleted = delete_unverify_contractor(db, contractor_id)
    return {
        "status": "success" if deleted else "failed"
    }


@r.get(
    "/{contractor_id}",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def get_any_unverified_contractor_details(
    contractor_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    """Get any Unverified Contractor account details"""
    contractor = get_single_unverified_contractor(db, contractor_id)
    try:
        get_contractor_data(contractor)  # add contractor extras
    except Exception as err:
        logger.error(f"Exception: {err}")
    return contractor


@r.patch(
    "/create",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def make_contractor_unverified(
    contractor_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    """Add contractor to unverified list"""
    contractor = unverify_contractor(db, contractor_id)
    try:
        get_contractor_data(contractor)  # add contractor extras
    except Exception as err:
        logger.error(f"Exception: {err}")
    return contractor

@r.patch(
    "/verify",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def verify_contractor(
    contractor_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    """Verify Contractor"""
    contractor = contractor_verify(db, contractor_id)
    try:
        get_contractor_data(contractor)  # add contractor extras
    except Exception as err:
        logger.error(f"Exception: {err}")
    return contractor
