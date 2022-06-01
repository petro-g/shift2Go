import typing as t

import firebase_admin
from app.db.session import SessionLocal
from app.db import crud
from dotenv import find_dotenv
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from app.config import constants
from app.celery_config.tasks.email import send_email_notification
from app.celery_config.celery_app import celery_app as celery
from app.db import models
from app.config.utils import check_found, get_module_logger

if not firebase_admin._apps:
    path = find_dotenv('firebase.json')
    cred = credentials.Certificate(path)
    firebase_app = firebase_admin.initialize_app(cred)

logger = get_module_logger(__name__)

@celery.task(name='send_notification_to_single_user')
def send_notification_to_single_user(registration_token):
    message = messaging.Message(
        notification=messaging.Notification(
            title='Test Message From Shift2Go',
            body='This is just a test message from Shift2Go backend using Firebase Cloud Messaging API',
        ),
        # data={
        #     'score': '850',
        #     'time': '2:45',
        # },
        token=registration_token,
    )
    response = messaging.send(message)
    if response is not None:
        logger.warn('List of tokens that caused failures: {0}'.format(
            registration_token))
    logger.info('Successfully sent message: %s', response)


@celery.task(name='send_firebase_push_with_payload')
def send_firebase_push_with_payload(user_id: int, title: str, message: str, payload: t.Optional[dict] = {}):
    db: Session = SessionLocal()
    user = crud.get_user_by_id(db, user_id)
    registration_tokens: t.List[str] = []
    if user.deviceTokens is not None:
        for id in user.deviceTokens:
            try:
                if id not in registration_tokens:
                    registration_tokens.append(id)
            except Exception as err:
                logger.error(f"Exception: {err}")
    else:
        return 'no user device token'

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=message,
        ),
        data=payload,
        tokens=registration_tokens,
    )
    response: messaging.BatchResponse = messaging.send_multicast(message)
    if response.failure_count > 0:
        responses = response.responses
        failed_tokens = []
        for idx, resp in enumerate(responses):
            if not resp.success:
                failed_tokens.append(registration_tokens[idx])

        logger.warn('List of tokens that caused failures: {0}'.format(
            failed_tokens))

    logger.info('{0} messages were sent successfully'.format(
        response.success_count))


def send_notification_to_multiple_users(notification: models.Notifications):
    if notification.notificationType == constants.NOTIFICATION_BOTH:
        send_firebase_push_notification.apply_async(kwargs={
            'notification_id': notification.id
        })
        send_email_notification.apply_async(kwargs={
            'notification_id': notification.id
        })
        # send_firebase_push_notification(notification.id)
        # send_email_notification(notification.id)
    elif notification.notificationType == constants.NOTIFICATION_PUSH:
        send_firebase_push_notification.apply_async(kwargs={
            'notification_id': notification.id
        })
        # send_firebase_push_notification(notification.id)
    else:
        send_email_notification.apply_async(kwargs={
            'notification_id': notification.id
        })
        # send_email_notification(notification.id)


@celery.task(name='send_firebase_push_notification')
def send_firebase_push_notification(notification_id: int):
    registration_tokens: t.List[str] = []
    db: Session = SessionLocal()
    notification = db.query(models.Notifications).filter(
        models.Notifications.id == notification_id).first()
    check_found(notification, f'Notification {notification_id}')
    for id in notification.receivers:
        try:
            user = crud.get_user_by_id(db, id)
            notification_settings = crud.get_notification_setting(db, user)
            if notification_settings.push and user.deviceTokens is not None:
                for token in user.deviceTokens:
                    if token not in registration_tokens:
                        registration_tokens.append(token)
        except Exception as err:
            logger.error(f"Exception: {err}")

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=notification.title,
            body=notification.message,
        ),
        # data={'score': '850', 'time': '2:45'},
        tokens=registration_tokens,
    )
    response: messaging.BatchResponse = messaging.send_multicast(message)
    if response.failure_count > 0:
        responses = response.responses
        failed_tokens = []
        for idx, resp in enumerate(responses):
            if not resp.success:
                failed_tokens.append(registration_tokens[idx])
        try:
            notification.failed = failed_tokens
            db.add(notification)
            db.commit()
        except Exception as err:
            logger.error(f"Exception: {err}")
        logger.warn('List of tokens that caused failures: {0}'.format(
            failed_tokens))

    logger.info('{0} messages were sent successfully'.format(
        response.success_count))

    db.close()
    return 'sent'


@celery.task(name='send_firebase_auto_push_notification')
def send_firebase_auto_push_notification(title: str, message: str, user_id: int):
    registration_tokens: t.List[str] = []
    db: Session = SessionLocal()
    user = crud.get_user_by_id(db, user_id)

    if user.deviceTokens is not None:
        for id in user.deviceTokens:
            try:
                if id not in registration_tokens:
                    registration_tokens.append(id)
            except Exception as err:
                logger.error(f"Exception: {err}")
    else:
        return 'no user device token'

    notification_message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=str(message)
        ),
        tokens=registration_tokens,
    )
    response: messaging.BatchResponse = messaging.send_multicast(notification_message)
    if response.failure_count > 0:
        responses = response.responses
        failed_tokens = []
        for idx, resp in enumerate(responses):
            if not resp.success:
                failed_tokens.append(registration_tokens[idx])
        logger.warn('List of tokens that caused failures: {0}'.format(
            failed_tokens))

    logger.info('{0} messages were sent successfully'.format(
        response.success_count))

    db.close()
    return 'sent'