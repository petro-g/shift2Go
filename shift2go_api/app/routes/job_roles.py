import typing as t

from app.config.auth import get_current_active_superuser, get_current_active_user
from app.config.utils import get_owner
from app.db import schemas
from app.db.crud import (add_jobrole, delete_jobrole, edit_jobrole,
                         get_jobrole, get_jobroles)
from app.db.session import get_db
from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)

jobrole_router = r = APIRouter()


@r.post(
    '/create',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.JobRolesOut,
    tags=['admin']
)
async def add_a_jobrole(
    request: schemas.JobRolesIn,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """
    Create a JobRoles
    """
    jobrole = add_jobrole(db, current_user,  request)
    get_owner(jobrole)
    return jobrole


@r.get(
    's',
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.JobRolesOut],
    tags=['admin', 'manager', 'contractor']
)
async def get_all_jobroles(
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """view all jobrole"""
    jobroles = get_jobroles(db)
    for jobrole in jobroles:
        get_owner(jobrole)
    return jobroles


@r.get(
    '/{jobrole_id}',
    status_code=status.HTTP_200_OK,
    response_model=schemas.JobRolesOut,
    tags=['admin', 'manager', 'contractor']
)
async def get_single_jobrole(
    jobrole_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """View any JobRole"""
    jobrole = get_jobrole(db,  jobrole_id)
    get_owner(jobrole)
    return jobrole


@r.post(
    '/update/{jobrole_id}',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.JobRolesOut,
    tags=['admin']
)
async def update_jobrole(
    jobrole_id: int,
    request: schemas.JobRolesEdit,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """
    Admin: Can edit any JobRole
    """
    jobrole = edit_jobrole(db,  request, jobrole_id)
    get_owner(jobrole)
    return jobrole


@r.delete(
    '/delete/{jobrole_id}',
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def delete_a_jobrole(
    jobrole_id: int,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """
    Admin: Can delete any JobRole
    """
    deleted = delete_jobrole(db,  jobrole_id)
    return {
        "status": "success" if deleted else "failed"
    }
