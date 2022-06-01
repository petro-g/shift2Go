import typing as t

from app.config.auth import (get_current_active_contractor,
                             get_current_active_contractor_or_admin,
                             get_current_active_superuser,
                             get_current_active_user)
from app.config.utils import get_certificate_data, process_header
from app.db import schemas
from app.db.crud import (add_certificate, create_certificate_type,
                         delete_certificate, edit_certificate,
                         edit_certificate_type, get_a_certificate_type,
                         get_certificate, get_certificate_types,
                         get_certificates, get_system_certificates)
from app.db.session import get_db
from fastapi import (APIRouter, Depends, HTTPException, Request, Response,
                     status)

certificate_router = r = APIRouter()


@r.post(
    '/create',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.CertificateOut,
    tags=['admin', 'contractor']
)
async def add_a_certificate(
    request: schemas.CertificateIn,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    """
    Create a Certificate
    """
    certificate = add_certificate(db, current_user,  request)
    get_certificate_data(certificate)
    return certificate

@r.get(
    's/all',
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.CertificateOut],
    tags=['admin']
)
async def get_all_system_certificates(
        response: Response,
        page: int = 1,
        current_user=Depends(get_current_active_superuser),
        db=Depends(get_db)
):
    """view all certificates on system"""
    pagination = get_system_certificates(db, page=page)
    for certificate in pagination.data:
        get_certificate_data(certificate)
    process_header(response, pagination, page)
    return pagination.data



@r.get(
    's',
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.CertificateOut],
    tags=['admin', 'manager', 'contractor']
)
async def get_all_certificates(
    response: Response,
    contractor_id: int = None,
    page: int = 1,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """view all certificate"""
    pagination = get_certificates(db, current_user, contractor_id=contractor_id, page=page)
    for certificate in pagination.data:
        get_certificate_data(certificate)
    process_header(response, pagination, page)
    return pagination.data


@r.get(
    '/types',
    status_code=status.HTTP_200_OK,
    response_model=t.List[schemas.CertificateTypeOut],
    tags=['admin', 'manager', 'contractor']
)
async def get_all_certificate_types(
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """view all Certificate Types"""
    certificates = get_certificate_types(db)

    return certificates


@r.get(
    '/{certificate_id}',
    status_code=status.HTTP_200_OK,
    response_model=schemas.CertificateOut,
    tags=['admin', 'manager', 'contractor']
)
async def get_single_certificate(
    certificate_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """View any certificate"""
    certificate = get_certificate(db, current_user,  certificate_id)
    get_certificate_data(certificate)
    return certificate


@r.patch(
    '/update/{certificate_id}',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.CertificateOut,
    tags=['admin', 'contractor']
)
async def update_certificate(
    certificate_id: int,
    request: schemas.CertificateEdit,
    current_user=Depends(get_current_active_contractor_or_admin),
    db=Depends(get_db)
):
    """
    Admin: Can edit any certificate
    """
    certificate = edit_certificate(db, current_user,  request, certificate_id)
    get_certificate_data(certificate)
    return certificate


@r.delete(
    '/delete/{certificate_id}',
    status_code=status.HTTP_200_OK,
    tags=['admin', 'contractor']
)
async def delete_a_certificate(
    certificate_id: int,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """
    Admin: Can delete any certificate
    """
    deleted = delete_certificate(db, current_user, certificate_id)
    return {
        "status": "success" if deleted else "failed"
    }


@r.post(
    '/type/create',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.CertificateTypeOut,
    tags=['admin']
)
async def add_a_certificate_type(
    request: schemas.CertificateTypeIn,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """
    Create a Certificate Type
    """
    certificate_type = create_certificate_type(db, request)
    return certificate_type


@r.get(
    '/type/{certificate_type_id}',
    status_code=status.HTTP_200_OK,
    # response_model=schemas.CertificateTypeOut,
    tags=['admin', 'manager', 'contractor']
)
async def get_single_certificate_type(
    certificate_type_id: int,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """View any certificate type"""
    certificate = get_a_certificate_type(db,  certificate_type_id)
    return certificate


@r.patch(
    '/type/update/{certificate_id}',
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.CertificateTypeOut,
    tags=['admin']
)
async def update_certificate(
    request: schemas.CertificateTypeEdit,
    current_user=Depends(get_current_active_superuser),
    db=Depends(get_db)
):
    """
    Admin: Can edit any certificate type
    """
    certificate = edit_certificate_type(db, request)
    return certificate
