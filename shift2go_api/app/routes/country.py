import typing as t

from app.config.auth import get_current_active_superuser, get_current_active_user
from app.db import schemas
from app.db.crud import (get_countries, get_country, create_country)
from app.db.session import get_db
from fastapi import APIRouter, Depends, status

country_router = r = APIRouter()

@r.post(
    "y/add",
    response_model=schemas.CountryOut,
    status_code=status.HTTP_201_CREATED,
    tags=['admin']
)
async def add_country(
    request: schemas.CountryIn,
    db=Depends(get_db),
    current_user=Depends(get_current_active_superuser)
):
    """
    Add a new Country
    """
    country = create_country(db, request)
    return country


@r.get(
    "ies",
    response_model=t.List[schemas.CountryOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def all_country_informations(
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View all Countrys on System
    """
    countrys = get_countries(db)
    return countrys


@r.get(
    "ies/{country_code}",
    response_model=schemas.CountryOut,
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor', 'manager']
)
async def get_country_information(
    country_code: str,
    db=Depends(get_db),
    current_user=Depends(get_current_active_user)
):
    """
    View a single Country
    """
    country = get_country(db, country_code.upper())
    return country
