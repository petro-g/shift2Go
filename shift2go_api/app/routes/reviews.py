from app.db.crud import get_all_given_reviews

from app.config.auth import (get_current_admin_or_manager,
                             get_current_active_manager_or_contractor,
                             get_current_active_superuser,
                             get_current_active_user)
from app.celery_config.tasks.utils import calculate_ratings
from app.config.utils import get_review_data, process_header
from app.db import schemas
from app.db.crud import (add_review, delete_review, edit_review, get_hotel_reviews, get_review, get_user_reviews)
from app.db.session import get_db
from fastapi import (APIRouter, Depends, Response, status)

review_router = r = APIRouter()


@r.post(
    "/add",
    # response_model=schemas.ReviewsOut,
    status_code=status.HTTP_201_CREATED,
    tags=['contractor', 'manager']
)
async def create_review(
    request: schemas.ReviewsIn,
    current_user=Depends(get_current_active_manager_or_contractor),
    db=Depends(get_db)
):
    review = add_review(db, current_user, request)
    get_review_data(review)
    calculate_ratings.apply_async(kwargs={
        'user_id': current_user.id,
        'review_id': review.id
    })
    return review


@r.get(
    "s/hotel",
    # response_model=t.List[schemas.ReviewsOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'manager', 'contractor']
)
async def get_a_hotels_reviews(
    hotel_id: int,
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    pagination = get_hotel_reviews(db, hotel_id, page=page)
    for review in pagination.data:
        get_review_data(review)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "s/user",
    # response_model=t.List[schemas.ReviewsOut],
    status_code=status.HTTP_200_OK,
    tags=['admin', 'manager']
)
async def get_all_user_reviews(
    user_id: int,
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    pagination = get_user_reviews(db, user_id, page=page)
    for review in pagination.data:
        get_review_data(review)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "s/me",
    # response_model=t.List[schemas.ReviewsOut],
    status_code=status.HTTP_200_OK,
    tags=['contractor']
)
async def get_my_reviews(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    pagination = get_user_reviews(db, current_user.id, page=page)
    for review in pagination.data:
        get_review_data(review)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "s/given",
    # response_model=t.List[schemas.ReviewsOut],
    status_code=status.HTTP_200_OK,
    tags=['contractor', 'manager']
)
async def get_reviews_ive_given(
    response: Response,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    pagination = get_all_given_reviews(db, current_user.id, page=page)
    for review in pagination.data:
        get_review_data(review)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    "/{review_id}",
    # response_model=schemas.ReviewsOut,
    status_code=status.HTTP_200_OK,
    tags=['admin', 'manager', 'contractor']
)
async def get_a_review(
    review_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    review = get_review(db, review_id)
    get_review_data(review)
    return review


@r.patch(
    "/edit",
    # response_model=schemas.ReviewsOut,
    status_code=status.HTTP_201_CREATED,
    tags=['manager', 'contractor']
)
async def edit_a_review(
    review_id: int,
    request: schemas.ReviewsEdit,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    review = edit_review(db, current_user, request, review_id)
    get_review_data(review)
    calculate_ratings.apply_async(kwargs={
        'user_id': current_user.id,
        'review_id': review.id
    })
    return review


@r.delete(
    "/delete",
    status_code=status.HTTP_200_OK,
    tags=['admin', 'manager', 'contractor']
)
async def delete_a_review(
    review_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    deleted = delete_review(db, current_user, review_id)
    return {
        "status": "success" if deleted else "failed"
    }
