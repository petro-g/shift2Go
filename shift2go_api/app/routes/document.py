import typing as t

from app.config.auth import (get_current_active_contractor,
                             get_current_active_contractor_or_admin,
                             get_current_active_user)
from app.config.utils import get_owner
from app.db import schemas
from app.db.crud import (create_document, edit_document, get_document,
                         get_documents)
from app.db.session import get_db
from fastapi import APIRouter, Depends, status

document_router = r = APIRouter()


@r.post(
    "/add",
    response_model=schemas.DocumentsOut,
    status_code=status.HTTP_201_CREATED,
    tags=['contractor']
)
async def add_document(
    request: schemas.DocumentsIn,
    current_user=Depends(get_current_active_contractor),
    db=Depends(get_db)
):
    document = create_document(db, current_user, request)
    get_owner(document)
    return document


@r.get(
    "s",
    response_model=t.List[schemas.DocumentsOut],
    status_code=status.HTTP_200_OK,
    tags=['contractor', 'admin']
)
async def get_all_documents(
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    documents = get_documents(db, current_user)
    for document in documents:
        get_owner(document)
    return documents


@r.get(
    "/{document_id}",
    response_model=schemas.DocumentsOut,
    status_code=status.HTTP_200_OK,
    tags=['contractor', 'manager', 'admin']
)
async def get_a_document(
    document_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    document = get_document(db, current_user, document_id)
    get_owner(document)
    return document


@r.patch(
    "/update/{document_id}",
    response_model=schemas.DocumentsOut,
    status_code=status.HTTP_201_CREATED,
    tags=['contractor', 'admin']
)
async def update_document(
    document_id: int,
    request: schemas.DocumentsEdit,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    document = edit_document(db, current_user, request, document_id)
    get_owner(document)
    return document
