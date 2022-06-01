import typing as t

from app.config.auth import get_current_active_superuser, get_current_active_user
from app.config.utils import get_owner, process_header
from app.db import schemas
from app.db.crud import (get_badge, get_badges, get_contractor_badges, get_hotel_badges, create_badge, delete_badge)
from app.db.session import get_db
from fastapi import APIRouter, Depends, Response, status

badge_router = r = APIRouter()

@r.post(
    "/add",
    response_model=schemas.BadgeOut,
    status_code=status.HTTP_201_CREATED,
    tags=['admin']
)
async def add_badge(
    request: schemas.BadgeIn,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Add a new Badge
    """
    badge = create_badge(db, current_user, request)
    get_owner(badge)
    return badge


@r.get(
    "s",
    response_model=t.List[schemas.BadgeOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def badge_informations(
    response: Response,
    page: int = 1,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View all Badges on System
    """
    pagination = get_badges(db, page)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "s/hotel",
    response_model=t.List[schemas.BadgeOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def hotel_badges(
    hotel_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View all Badges earned by Hotel
    """
    badges = get_hotel_badges(db, current_user, hotel_id)
    return badges


@r.get(
    "s/contractor",
    response_model=t.List[schemas.BadgeOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def contractor_badges(
    contractor_id: int = None,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View all Badges earned by Contractor
    """
    badges = get_contractor_badges(db, current_user, contractor_id)
    return badges


@r.get(
    "/{badge_id}",
    response_model=schemas.BadgeOut,
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def get_badge_information(
    badge_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View a single Badge
    """
    badge = get_badge(db, badge_id)
    get_owner(badge)
    return badge


@r.delete(
    "/delete/{badge_id}",
    status_code=status.HTTP_200_OK,
    tags=['admin']
)
async def delete_badge_informations(
    badge_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Delete a Badge
    """
    deleted = delete_badge(db, current_user, badge_id)
    return {
        "status": "success" if deleted else "failed"
    }
