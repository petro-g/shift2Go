import random
import string
import time

import uvicorn
from fastapi import (BackgroundTasks, Depends, FastAPI, Response)
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes.admin import admin_router
from app.routes.auth import auth_router
from app.routes.badge import badge_router
from app.routes.bank import bank_router
from app.routes.billing import billing_router
from app.routes.cancellation import cancelled_router
from app.routes.certificate import certificate_router
from app.routes.contractor import contractor_router
from app.routes.country import country_router
from app.routes.document import document_router
from app.routes.hotel import hotel_router
from app.routes.job_roles import jobrole_router
from app.routes.manager import manager_router
from app.routes.notification import notification_router
from app.routes.reviews import review_router
from app.routes.shift import shift_router
from app.routes.socket import socket_router
from app.routes.request import request_router
from app.routes.unverified_contractor import \
    unverified_contractor_router
from app.config import config
from app.config.auth import get_current_active_user
from app.celery_config.tasks.email import send_test_email
from app.celery_config.tasks.notification import send_notification_to_single_user
from app.db import models
from app.db.crud import create_test_super_admin, get_user_by_email
# from app.config.celery_app import celery_app
from app.db.session import SessionLocal, engine, get_db

from app.celery_config.celery_app import example_task

# create tables if using local database
from app.config.utils import get_module_logger

models.Base.metadata.create_all(bind=engine)

logger = get_module_logger(__name__)


def create_app():
    app = FastAPI(
        title=config.PROJECT_NAME, docs_url="/api/docs", redoc_url='/api/redoc', openapi_url="/api"
    )

    origins = [
        'http://localhost:3000',
        'http://localhost',
        'https://3.130.10.151',
        'http://3.130.10.151',
        'https://shifts2go.com',
        'http://shifts2go.com',
        'http://0.0.0.0',
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
        expose_headers=['page', 'per_page', 'page_count', 'total_count']
    )

    # Web Socket
    app.include_router(
        socket_router,
    )

    # Routers
    app.include_router(
        admin_router,
        prefix="/api/v1/admin",
        tags=['admin']
    )
    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
    )
    app.include_router(
        bank_router,
        prefix="/api/v1/bank",
    )
    app.include_router(
        badge_router,
        prefix="/api/v1/badge",
    )
    app.include_router(
        contractor_router,
        prefix="/api/v1/contractor",
    )
    app.include_router(
        certificate_router,
        prefix="/api/v1/certificate",
    )
    app.include_router(
        jobrole_router,
        prefix="/api/v1/job_role",
    )
    app.include_router(
        unverified_contractor_router,
        prefix="/api/v1/unverified_contractor",
    )
    app.include_router(
        manager_router,
        prefix="/api/v1/manager",
    )
    app.include_router(
        hotel_router,
        prefix="/api/v1/hotel",
    )
    app.include_router(
        shift_router,
        prefix="/api/v1/shift",
    )
    app.include_router(
        review_router,
        prefix="/api/v1/review",
    )
    app.include_router(
        cancelled_router,
        prefix="/api/v1/shift_cancellation",
    )
    app.include_router(
        billing_router,
        prefix="/api/v1/billing",
    )
    app.include_router(
        notification_router,
        prefix="/api/v1/notification",
    )
    app.include_router(
        country_router,
        prefix="/api/v1/countr",
    )
    app.include_router(
        document_router,
        prefix="/api/v1/document",
    )

    app.include_router(
        request_router,
        prefix="/api/v1/shifts_request",
    )

    return app


app = create_app()


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
    response = await call_next(request)
    request.state.db.close()
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    idem = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    logger.info(f"rid={idem} start request path={request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    logger.info(f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}")
    logger.info(f"message={response}")

    return response


@app.middleware("http")
async def error_handle(request: Request, call_next):
    response = await call_next(request)
    if response.status_code >= 400:
        logger.error(f"Error:{response}")
    return response


@app.get("/api/v1")
async def root():
    return {"message": "Hello World"}


@app.get("/api/v1/task")
async def example_tasks(
        background_task: BackgroundTasks,
        db=Depends(get_db)
):
    example_task.apply_async(kwargs={
        'word': 'Hello World'
    })
    # new_message.apply_async()
    # background_task.add_task(new_message)
    return {"results": 'done'}


@app.post(
    '/api/v1/test_push'
)
async def send_firebase_push_notification(
        token: str,
        current_user=Depends(get_current_active_user)
):
    send_notification_to_single_user.apply_async(kwargs={
        'registration_token': token
    })
    return 'sent'


@app.post(
    '/api/v1/test_email'
)
async def send_email(
        email: str,
        background_task: BackgroundTasks,
        current_user=Depends(get_current_active_user)
):
    return send_test_email(email)
    # background_task.add_task(send_test_email, email, current_user.id)
    return 'sent'


@app.get(
    '/api/v1/auth/shift2go_admin'
)
async def create_super_user(
        response: Response,
        db=Depends(get_db)
):
    email = 'admin@shift2go.com'
    user = get_user_by_email(db, email)
    if user:
        return {
            "message": "This is your superuser credentials",
            "email": "admin@shift2go.com",
            "password": "password",
            "superuser": user
        }
    new_admin = create_test_super_admin(db)
    return {
        "message": "This is your superuser credentials",
        "email": "admin@shift2go.com",
        "password": "password",
        "superuser": new_admin
    }


if __name__ == "__main__":
    if config.LOCAL_HOST is not None and config.LOCAL_PORT is not None:
        uvicorn.run("main:app", host=config.LOCAL_HOST, reload=True, port=config.LOCAL_PORT)
    uvicorn.run("main:app", reload=True)
