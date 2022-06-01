from fastapi import Response
from sqlalchemy.orm import Session
from app.db import models, schemas
import typing as t
from datetime import datetime, timedelta

from app.config import constants, security
from app.db.models import User, Shifts, Billings
from fastapi import status, HTTPException
import logging

from app.config.config import PAGE_LIMIT

def get_module_logger(mod_name):
    """
    To use this, do logger = get_module_logger(__name__)
    """
    logger = logging.getLogger(mod_name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger

logger = get_module_logger(__name__)

def check_found(item: t.Any, name: str):
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} Information not found")


def generate_verification_token(user_id: str, email: str):
    token_expiry_date = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_verify_token(
        data={"email": email, "user_id": user_id,
              'type': constants.EMAIL_VERIFICATION_TYPE}
    )
    tk = schemas.Token(access_token=access_token, token_type='bearer')
    return tk.access_token


def generate_password_reset_token(email: str):
    token_expiry_date = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_verify_token(
        data={"email": email, "type": constants.PASSWORD_CONFIRM_TYPE}
    )
    tk = schemas.Token(access_token=access_token, token_type='bearer')
    return tk.access_token


def generate_password_change_token(user: User):
    token_expiry_date = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_verify_token(
        data={"email": user.email, "user_id": user.id,
              "type": constants.PASSWORD_CHANGE_TYPE}
    )
    tk = schemas.Token(access_token=access_token, token_type='bearer')
    return tk.access_token


def generate_email_login_token(user: User):
    token_expiry_date = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_verify_token(
        data={"email": user.email, "user_id": user.id,
              "type": constants.EMAIL_LOGIN_TOKEN_TYPE}
    )
    tk = schemas.Token(access_token=access_token, token_type='bearer')
    return tk.access_token


def get_owner(data: t.Any):
    try:
        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # del data.owner.deviceTokens
        # del data.owner.is_superuser
    except Exception as err:
        logger.error(f"Exception: {err}")


def get_certificate_data(data: t.Any):
    try:
        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # del data.owner.deviceTokens
        # del data.owner.is_superuser
    except Exception as err:
        logger.error(f"Exception: {err}")

    try:
        data.type
    except Exception as err:
        logger.error(f"Exception: {err}")

def get_hotel_data(data: t.Any):
    try:
        try:
            data.manager
            get_owner(data.manager)
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.bank
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.favourites
        except Exception as err:
            logger.error(f"Exception: {err}")
    except Exception as err:
        logger.error(f"Exception: {err}")


def get_manager_data(data: t.Any, show_token: t.Optional[bool] = False):
    try:
        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # if not show_token:
        #     del data.owner.deviceTokens
        # del data.owner.is_superuser
        try:
            data.hotels
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.notification
        except Exception as err:
            logger.error(f"Exception: {err}")
    except Exception as err:
        logger.error(f"Exception: {err}")


def get_bill_data(data: t.Any):
    try:

        try:
            data.shift
            try:
                data.shift.roles
            except Exception as err:
                logger.error(f"Exception: {err}")

        except Exception as err:
            logger.error(f"Exception: {err}")

        try:
            data.hotel
        except Exception as err:
            logger.error(f"Exception: {err}")

        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # del data.owner.deviceTokens
        # del data.owner.is_superuser

    except Exception as err:
        logger.error(f"Exception: {err}")


def get_cancelled_shift_data(data: t.Any):
    try:

        try:
            data.shift
        except Exception as err:
            logger.error(f"Exception: {err}")

        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # del data.owner.deviceTokens
        # del data.owner.is_superuser

    except Exception as err:
        logger.error(f"Exception: {err}")


def get_request_shift_data(data: t.Any):
    try:

        try:
            data.shift
        except Exception as err:
            logger.error(f"Exception: {err}")

        try:
            data.contractor
            get_contractor_data(data.contractor)
        except Exception as err:
            logger.error(f"Exception: {err}")


        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # del data.owner.deviceTokens
        # del data.owner.is_superuser

    except Exception as err:
        logger.error(f"Exception: {err}")


def get_notification_data(data: t.Any):
    try:

        data.sender  # add owner
        # del data.sender.hashed_password  # removed hashed password
        # del data.sender.deviceTokens
        # del data.sender.is_superuser

    except Exception as err:
        logger.error(f"Exception: {err}")


def get_shift_data(data: t.Any, show_user: t.Optional[bool] = False):
    try:
        try:
            data.contractor
            # if show_user and data.status == constants.SHIFT_ACCEPTED:
            try:
                data.contractor.owner
                # del data.contractor.owner.hashed_password  # removed hashed password
                # del data.contractor.owner.deviceTokens
                # del data.contractor.owner.is_superuser

                try:
                    data.contractor.roles
                except Exception as err:
                    logger.error(f"Exception: {err}")

            except Exception as err:
                logger.error(f"Exception: {err}")
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.hotel
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.manager
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.roles
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.certificates_types
        except Exception as err:
            logger.error(f"Exception: {err}")

        try:
            data.requests
            for request in data.requests:
                try:
                    request.contractor
                    get_contractor_data(data.contractor)
                except Exception as err:
                    logger.error(f"Exception: {err}")
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.reviews
        except Exception as err:
            logger.error(f"Exception: {err}")

        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # del data.owner.deviceTokens
        # del data.owner.is_superuser

    except Exception as err:
        logger.error(f"Exception: {err}")


def get_contractor_data(data: t.Any, delete_token: t.Optional[bool] = True):
    try:
        try:
            data.roles
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.certificates
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.reviews
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.bank
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.documents
        except Exception as err:
            logger.error(f"Exception: {err}")
        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # if delete_token:
        #     del data.owner.deviceTokens
        # del data.owner.is_superuser

    except Exception as err:
        logger.error(f"Exception: {err}")


def get_review_data(data: t.Any):
    try:
        try:
            data.shift
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.owner
        except Exception as err:
            logger.error(f"Exception: {err}")
        try:
            data.badge
        except Exception as err:
            logger.error(f"Exception: {err}")
        data.owner  # add owner
        # del data.owner.hashed_password  # removed hashed password
        # del data.owner.deviceTokens
        # del data.owner.is_superuser

    except Exception as err:
        logger.error(f"Exception: {err}")


def get_billed(data: t.Any):
    try:
        data.owner  # add owner
        del data.owner.hashed_password  # removed hashed password
        del data.owner.deviceTokens
        del data.owner.is_superuser
        data.contracts
        data.billed
    except Exception as err:
        logger.error(f"Exception: {err}")


class Pagination:
    data: t.Any
    count: int

    def __init__(self, data: t.Any, count: int) -> None:
        self.data = data
        self.count = count


def process_header(response: Response, pagination: Pagination, page: int) -> None:
    # This is necessary for react-admin to work
    try:
        response.headers["Content-Range"] = f"0-9/{len(pagination.data)}"
        response.headers.append(key='page', value=str(page))
        response.headers.append(key='per_page', value=str(PAGE_LIMIT))
        page_count = pagination.count / PAGE_LIMIT
        if '.' in str(page_count):
            rem = str(page_count)[str(page_count).index('.') + 1:]
            page_count = int(page_count) + \
                1 if int(rem) > 0 else int(page_count)
        response.headers.append(key='page_count', value=str(page_count))
        response.headers.append(key='total_count', value=str(pagination.count))
    except Exception as err:
        logger.error(f"Exception: {err}")


def generate_accepted_shift_notification_message(shift: Shifts, user: User) -> str:
    return f'The Shift {shift.name} has been accepted by {user.firstname}. Please check the platform for more information'


def generate_decline_shift_notification_message(shift: Shifts, user: User) -> str:
    return f'The Shift {shift.name} has been decline by {user.firstname}. Please check the platform for more information'


def generate_awarded_shift_notification_message(shift: Shifts, user: User) -> str:
    return f'The Shift {shift.name} has been awarded to you. Please check the platform for more information',


def generate_shift_clockout_notification_message(shift: Shifts, user: User, bill: Billings) -> str:
    return f'The Shift {shift.name} as ended. You will be paid ${bill.amountPayableToContractor}. Please check the platform for more information',


def generate_upcoming_shift_notification_message(shift: Shifts, user: User) -> str:
    diff = shift.startTime - datetime.utcnow()
    days, seconds = diff.days, diff.seconds
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    hour = days * 24 + seconds // 3600
    return f'The Shift {shift.name} starts in {hour} hour {minutes} minutes at {shift.startTime.time().hour}:{shift.startTime.time().minute}. Please check the platform for more information'


def generate_shift_request_notification_message(shift: Shifts, user: User) -> str:
    return f'The Shift {shift.name} has been request by {user.firstname}. Please check the platform for more information'


def generate_shift_completed_notification_message(shift: Shifts, user: User) -> str:
    return f'The Shift {shift.name} has been completed by {user.firstname}. Please check the platform for more information'
