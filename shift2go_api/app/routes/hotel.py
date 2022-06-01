import typing as t

from app.config.auth import (get_current_active_manager, get_current_active_user,
                             get_current_admin_or_manager, get_unverified_current_active_manager)
from app.config.utils import (get_contractor_data, get_hotel_data, get_owner,
                              process_header)
from app.db import schemas
from app.db.crud import (add_hotel, delete_hotel, edit_hotel, add_hotel_favourite_contractor, remove_hotel_favourite_contractor,
                         get_favourite_contractors, get_hotel, get_hotels)
from app.db.session import get_db
from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)

hotel_router = r = APIRouter()


@r.post(
    '/create',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.HotelOut,
    tags=['manager']
)
async def add_a_hotel(
    request: schemas.HotelIn,
    current_user=Depends(get_unverified_current_active_manager),
    db=Depends(get_db)
):
    """
    Create a Hotel
    """
    hotel = add_hotel(db, current_user, request)
    get_hotel_data(hotel)
    return hotel


@r.get(
    's',
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.HotelOut],
    tags=['admin', 'manager', 'contractor']
)
async def get_all_hotels(
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """
    Contractor: Can view all hotel
    Admin: Can view all hotel
    Hotel Manager: Can view all their hotels
    """
    hotels = get_hotels(db, current_user)
    for hotel in hotels:
        get_hotel_data(hotel)
    return hotels


@r.get(
    '/favourites',
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.ContractorOut],
    tags=['admin', 'manager']
)
async def get_hotel_favourite_contractors(
    hotel_id: int,
    response: Response,
    job_role_id: int = None,
    page: int = 1,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Get Hotel favourite contractors
    """
    pagination = get_favourite_contractors(db, current_user, page, hotel_id, job_role_id)
    for contractor in pagination.data:
        get_contractor_data(contractor)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    '/favourites/add',
    status_code=status.HTTP_200_OK,
    # response_model=t.List[schemas.HotelOut],
    tags=['admin', 'manager']
)
async def add_contractor_to_hotel_favourites(
    hotel_id: int,
    contractor_id: int,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Add Contractor to Hotel favourite contractors
    """
    hotel = add_hotel_favourite_contractor(
        db, current_user, contractor_id, hotel_id)
    get_hotel_data(hotel)
    return hotel


@r.get(
    '/favourites/remove',
    status_code=status.HTTP_200_OK,
    # response_model=t.List[schemas.HotelOut],
    tags=['admin', 'manager']
)
async def remove_contractor_from_hotel_favourites(
    hotel_id: int,
    contractor_id: int,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Remove Contractor to Hotel favourite contractors
    """
    hotel = remove_hotel_favourite_contractor(
        db, current_user, contractor_id, hotel_id)
    get_hotel_data(hotel)
    return hotel


@r.get(
    '/{hotel_id}',
    status_code=status.HTTP_200_OK,
    response_model=schemas.HotelOut,
    tags=['admin', 'manager', 'contractor']
)
async def get_single_hotel(
    hotel_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """
    Contractor: Can view any hotel
    Admin: Can view any hotel
    Hotel Manager: Can view their own hotel
    """
    hotel = get_hotel(db, current_user, hotel_id)
    get_hotel_data(hotel)
    return hotel


@r.patch(
    '/update/{hotel_id}',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.HotelOut,
    tags=['admin', 'manager']
)
async def update_hotel(
    hotel_id: int,
    request: schemas.HotelEdit,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Admin: Can edit any hotel
    Hotel Manager: Can edit their own hotel
    """
    hotel = edit_hotel(db, current_user, request, hotel_id)
    get_hotel_data(hotel)
    return hotel


@r.delete(
    '/delete/{hotel_id}',
    status_code=status.HTTP_200_OK,
    tags=['manager', 'admin']
)
async def delete_a_hotel(
    hotel_id: int,
    current_user=Depends(get_current_admin_or_manager),
    db=Depends(get_db)
):
    """
    Hotel Manager: Can delete their own hotel
    Admin: Can delete any hotel
    """
    deleted = delete_hotel(db, current_user, hotel_id)
    return {
        "status": "success" if deleted else "failed"
    }
