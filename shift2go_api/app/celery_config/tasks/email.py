import typing as t
from json import JSONDecodeError

import requests
from app.celery_config.celery_app import celery_app as celery
from app.config.config import (DOMAIN, DOMAIN_LOCAL, MAILGUN_API_KEY,
                               MAILGUN_DOMAIN, FRONTEND_DOMAIN, BACKEND_DOMAIN)
from app.config.security import SECRET_KEY
from app.config.utils import check_found, get_module_logger
from app.db import crud, models
from app.db.models import User
from app.db.schemas import Token
from app.db.session import SessionLocal
from sqlalchemy.orm import Session

logger = get_module_logger(__name__)


@celery.task(name='send_test_email')
def send_test_email(email: str):

    template = f"""
        <!DOCTYPE html>
        <html>
            <head>Shift2Go Email Test</head>
            <body>
            <h3>This is a test email</h3>
            </body>
        </html>
    """

    return send_mailgun_email('Shift2Go Test Email', template, [email])


@celery.task(name='send_email_login_email')
def send_email_login_email(user_id: int, token: str):

    user: User = None
    db: Session = SessionLocal()
    user = crud.get_user_by_id(db, user_id)
    db.close()
    tk = Token(access_token=token)
    template = f"""
        <!DOCTYPE html>
        <html>
            <head>Shift2Go Email Login</head>
            <body>
            <h3>Email Login</h3>
            <p> Hello {user.firstname}</p>
            <p>Please you requested login. Login  </p>
            <a href="{DOMAIN_LOCAL}/api/v1/auth/token_login?token={tk.access_token}">here</a>
            </body>
        </html>
    """

    return send_mailgun_email('Complete your login into Shift2Go', template, [user.email])


@celery.task(name='send_email_verification')
def send_email_verification(user_id: int, token: str):
    try:
        user: User = None
        db: Session = SessionLocal()
        user = crud.get_user_by_id(db, user_id)
        db.close()

        tk = Token(access_token=token)
        template = f"""
            <!DOCTYPE html>
            <html>
                <head>Shift2Go Email Verification</head>
                <body>
                <h3>Account Verification</h3>
                <p> Hello {user.firstname}</p>
                <p>Please verify your email by clicking </p>
                <a href="{FRONTEND_DOMAIN}/verify-email?token={tk.access_token}">here</a>
                </body>
            </html>
        """
        return send_mailgun_email('Shift2Go Email Verification', template, [user.email])

    except Exception as err:
        logger.error(f"Exception: {err}")


@celery.task(name='send_password_reset')
def send_password_reset(user_id: int, token: str):

    user: User = None
    db: Session = SessionLocal()
    user = crud.get_user_by_id(db, user_id)
    db.close()

    tk = Token(access_token=token)
    template = f"""
        <!DOCTYPE html>
        <html>
            <head>Shift2Go Password Reset</head>
            <body>
            <p> Hello {user.firstname}, </p>
            <p>Please reset your password by clicking this link </p>
            <a href="{FRONTEND_DOMAIN}/reset-password?token={tk.access_token}">Reset Password</a>
            </body>
        </html>
    """

    return send_mailgun_email('Shift2Go Password Reset', template, [user.email])


@celery.task(name='send_email_notification')
def send_email_notification(notification_id: int) -> None:
    try:
        db: Session = SessionLocal()
        notification = db.query(models.Notifications).filter(
            models.Notifications.id == notification_id).first()
        check_found(notification, f'Notification {notification_id}')
        emails: t.List[str] = []
        for id in notification.receivers:
            try:
                user = crud.get_user_by_id(db, id)
                notification_settings = crud.get_notification_setting(db, user)
                if notification_settings.email:
                    emails.append(user.email)
            except Exception:
                logger.error(f"Exception: {Exception.with_traceback()}")

        db.close()
        template = f"""
                <!DOCTYPE html>
                <html>
                    <head> {notification.title} </head>
                    <body>
                    <p> {notification.message} </p>
                    </body>
                </html>
            """

        return send_mailgun_email(notification.title, template, emails)

    except Exception as err:
        logger.error(f"Exception: {err}")


@celery.task(name='send_email_auto_notification')
def send_email_auto_notification(title: str, message: str, email: str):
    template = f"""
            <!DOCTYPE html>
            <html>
                <head> {title} </head>
                <body>
                <p> {message} </p>
                </body>
            </html>
        """

    return send_mailgun_email(title, template, [email])


# send email with mailgun api
def send_mailgun_email(subject: str, html: str, receivers: t.List[str]):
    request = requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"Shift2Go <no-reply@{MAILGUN_DOMAIN}>",
            "to": receivers,
            "subject": subject,
            "html": html
        }
    )
    if request.ok:
        try:
            return request.json()
        except JSONDecodeError as error:
            logger.error(f"Exception: {error}")
            return 'Domain Error'
        except Exception as err:
            logger.error(f"Exception: {err}")
            return 'failed'

    else:
        try:
            return request.json()
        except Exception as err:
            logger.error(f"Exception: {err}")
            return 'failed'
