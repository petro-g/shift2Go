import typing as t

from app.config.auth import (generate_login_token, get_current_active_contractor,
                             get_current_active_superuser)
from app.celery_config.tasks.email import send_email_verification
from app.config.utils import (generate_verification_token, process_header, get_contractor_data, get_module_logger)
from app.db import schemas
from app.db.crud import (contractor_signup, delete_contractor, get_contractor,
                         get_contractors, get_single_verified_contractor,
                         update_contractor)
from app.db.session import get_db
from fastapi import (APIRouter, BackgroundTasks, Depends, Request, Response,
                     status)

contractor_router = r = APIRouter()
logger = get_module_logger(__name__)

@r.post(
    "/signup",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_201_CREATED,
    tags=['contractor']
)
async def signup_contractor(
    request: schemas.ContractorIn,
    response: Response,
    background_task: BackgroundTasks,
    db=Depends(get_db)
):
    contractor = contractor_signup(db, request)
    get_contractor_data(contractor)
    # send_email_verification(
    #     contractor.owner.id,
    #     generate_verification_token(contractor.owner.id, contractor.owner.email)
    # )
    # background_task.add_task(
    #     send_email_verification,
    #     contractor.owner.id,
    #     generate_verification_token(contractor.owner.id, contractor.owner.email)
    # )
    response.headers['Authorization'] = f'Bearer {generate_login_token(contractor.owner)}'

    return contractor


@r.get(
    "/me",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_200_OK,
    tags=['contractor']
)
async def contractor_information(
    db=Depends(get_db),
    current_user=Depends(get_current_active_contractor)
):
    contractor = get_contractor(db, current_user)
    get_contractor_data(contractor, delete_token=False)
    return contractor


@r.get(
    "s",
    response_model=t.List[schemas.ContractorOut],
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def all_system_contractors(
    response: Response,
    page: int = 1,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    """
    Get all Contractors on system
    """
    pagination = get_contractors(db, page)
    for contractor in pagination.data:
        try:
            get_contractor_data(contractor)  # add contractor extras
        except Exception as err:
            logger.error(f"Exception: {err}")
    # This is necessary for react-admin to work
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/{contractor_id}",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def get_any_contractor_details(
    request: Request,
    contractor_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    """Get any Contractor account details"""
    contractor = get_single_verified_contractor(db, contractor_id)
    try:
        get_contractor_data(contractor)  # add contractor extras
    except Exception as err:
        logger.error(f"Exception: {err}")
    return contractor


@r.patch(
    "/update/me",
    response_model=schemas.ContractorOut,
    status_code=status.HTTP_201_CREATED,
    tags=['contractor']
)
async def update_contractor_information(
    request: schemas.ContractorEdit,
    db=Depends(get_db),
    current_user=Depends(get_current_active_contractor)
):
    contractor = update_contractor(db, current_user, request)
    get_contractor_data(contractor, delete_token=False)
    return contractor


@r.delete(
    "/delete/{contractor_id}",
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def delete_a_contractor(
    contractor_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    deleted = delete_contractor(db, contractor_id)
    return {
        "status": "success" if deleted else "failed"
    }
