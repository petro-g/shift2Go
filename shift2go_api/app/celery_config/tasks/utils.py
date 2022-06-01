import typing as t
from datetime import datetime, timedelta

from app.config import constants
from app.celery_config.celery_app import celery_app as celery
from app.celery_config.tasks import notification, email
from app.config.utils import check_found
from app.db import crud, models, schemas
from app.db.session import SessionLocal
from sqlalchemy.orm import Session


@celery.task(name='calculate_ratings')
def calculate_ratings(user_id: int, review_id: int):

    user: models.User = None
    review: models.Reviews = None
    db: Session = SessionLocal()
    user = crud.get_user_by_id(db, user_id)
    review = crud.get_review(db, review_id)

    if review.reviewee_type == constants.REVIWEE_TYPE_HOTEL:
        hotel = db.query(models.Hotels).filter(
            models.Hotels.id == review.reviewee_id).first()
        check_found(hotel, 'Hotel')
        reviews = db.query(models.Reviews).filter(
            models.Reviews.reviewee_id == hotel.id,
            models.Reviews.reviewee_type == constants.REVIWEE_TYPE_HOTEL
        ).all()

        total = 0
        for item in reviews:
            total += item.rating

        rating = total / len(reviews)

        hotel.rating = rating
        db.add(hotel)
        db.commit()

    else:
        user = db.query(models.User).filter(
            models.User.id == review.reviewee_id).first()
        check_found(user, 'User')
        reviews = db.query(models.Reviews).filter(
            models.Reviews.reviewee_id == user.id,
            models.Reviews.reviewee_type == constants.REVIWEE_TYPE_USER
        ).all()

        total = 0
        for item in reviews:
            total += item.rating

        rating = total / len(reviews)

        contractor = db.query(models.Contractors).filter(
            models.Contractors.userID == user.id).first()
        check_found(contractor, 'Contractor')
        contractor.rating = rating
        badge_count = 0
        for review in reviews:
            badge_count = badge_count + 1 if review.badge_id is not None else badge_count + 0
        contractor.badge_count = badge_count
        db.add(contractor)
        db.commit()

    db.close()


def get_hours_between_dates(now: datetime, future: datetime) -> int:

    diff = future - now

    days, seconds = diff.days, diff.seconds
    # minutes = (seconds % 3600) // 60
    # seconds = seconds % 60
    return days * 24 + seconds // 3600


@celery.task(name='shift_cancellation')
def shift_cancellation(user_id: int, token: str):
    db: Session = SessionLocal()
    cancellations = db.query(models.ShiftCancellations).filter(
        models.ShiftCancellations.cancelledBy == user_id,
    ).order_by(models.ShiftCancellations.createdAt.desc()).all()

    penalty_cancellations: t.List[models.ShiftCancellations] = []
    for cancelled_item in cancellations:
        shift = crud.get_shift_by_id(db, cancelled_item.shift_id)
        penalty_range = shift.startTime - timedelta(hours=12)

        if cancelled_item.createdAt >= penalty_range:
            penalty_cancellations.append(cancelled_item)

    penalties_len = len(penalty_cancellations)

    latest_cancel = penalty_cancellations[0]
    shift = crud.get_shift_by_id(db, latest_cancel.shift_id)
    # hours_before = get_hours_between_dates(datetime.utcnow(), shift.startTime)

    # get shifts cancelled within 12 hours before shift

    if penalties_len == 1:
        send_cancellation_notification(
            db=db,
            user_id=user_id,
            title='You have cancelled a Shift',
            message='You must call Shift2Go and explain why you cancelled a shift 12 before the shift starts'
        )
    elif penalties_len == 2:
        first = penalty_cancellations[0]
        current = datetime.utcnow()
        diff = current - first.createdAt
        if diff.days <= 45:
            crud.logout_user(db, token)
            # deactivate user
            suspend_user(db, user_id)

            future = current + timedelta(days=14)
            # activate user after 15 or 30 days
            reactivate_user.apply_async(kwargs={
                'user_id': user_id
            }, eta=future)
            send_cancellation_notification(
                db=db,
                user_id=user_id,
                title='You have cancelled a Shift',
                message='This is the second shift you have cancelled in a 45 days period, therefore you account have been suspended for 14 days. You also need to call Shift2go'
            )
    elif penalties_len == 3:
        first = penalty_cancellations[0]
        current = datetime.utcnow()
        diff = current - first.createdAt
        if diff.days <= 45:
            crud.logout_user(db, token)
            # deactivate user
            suspend_user(db, user_id)

            future = current + timedelta(days=30)
            # activate user after 15 or 30 days
            reactivate_user.apply_async(kwargs={
                'user_id': user_id
            }, eta=future)
            send_cancellation_notification(
                db=db,
                user_id=user_id,
                title='You have cancelled a Shift',
                message='This is the third shift you have cancelled in a 45 days period, therefore you account have been suspended for 30 days'
            )
    elif penalties_len == 4:

        crud.logout_user(db, token)
        # deactivate user
        suspend_user(db, user_id)

        send_cancellation_notification(
            db=db,
            user_id=user_id,
            title='You have cancelled a Shift',
            message='This is the fourth shift you have cancelled in a 45 days period, therefore you account have been suspended'
        )

    else:
        crud.logout_user(db, token)
        # deactivate user
        suspend_user(db, user_id)

        send_cancellation_notification(
            db=db,
            user_id=user_id,
            title='You have cancelled a Shift',
            message='Your account have been suspended indefinately'
        )

    db.close()


@celery.task(name='reactivate_user')
def reactivate_user(user_id: int):
    db: Session = SessionLocal()
    user = crud.get_user_by_id(db, user_id)
    user.is_active = True
    db.add(user)
    db.commit()

    contractor = crud.get_contractor_by_user_id(db, user.id)
    contractor.verified = True
    db.add(contractor)
    db.commit()
    db.close()


@celery.task(name='shift_clock_in_logic')
def shift_clock_in_logic(shift_id: int):
    db: Session = SessionLocal()
    shift = crud.get_shift_by_id(db, shift_id)
    if not shift.status == constants.SHIFT_ONGOING:
        if shift.contractor_id is not None:
            contractor = crud.get_contractor_by_id(db, shift.contractor_id)
            title = f'Shift offer Rescinded'
            message = f'The shift {shift.name} has been disabled because you failed to clock in 15 after the start time'
            user = crud.get_user_by_id(db, contractor.userID)
            notification_settings = crud.get_notification_setting(db, user)
            if notification_settings.push:
                notification.send_firebase_auto_push_notification.apply_async(kwargs={
                    'title': title,
                    'message': message,
                    'user_id': contractor.userID
                })
            if notification_settings.email:
                email.send_email_auto_notification.apply_async(kwargs={
                    'title': title,
                    'message': message,
                    'email': user.email
                })

        shift.status = constants.SHIFT_PENDING
        shift.contractor_id = None
        shift.active = False
        shift.audienceType = constants.AUDIENCE_TYPE_MARKET
        db.add(shift)
        db.commit()
    db.close()


@celery.task(name='shift_clock_out_logic')
def shift_clock_out_logic(shift_id: int):
    db: Session = SessionLocal()
    shift = crud.get_shift_by_id(db, shift_id)
    if shift.contractor_id is not None and shift.endedAt is None:
        contractor = crud.get_contractor_by_id(db, shift.contractor_id)
        user = crud.get_user_by_id(db, contractor.userID)
        request = schemas.ClockOut(
            shift_id=shift.id,
            clockOutLatitude=0,
            clockOutLongitude=0
        )
        crud.end_shift(db, user, request)

        notification_settings = crud.get_notification_setting(db, user)
        if notification_settings.push:
            notification.send_firebase_push_with_payload.apply_async(kwargs={
                'user_id': user.id,
                'title': 'Shift Ended',
                'message': f'The shift {shift.name} has ended. Please rate the hotel',
                'payload': {
                    'shift_id': shift.id,
                    'hotel_id': shift.hotel_id
                }
            })
        if notification_settings.email:
            email.send_email_auto_notification.apply_async(kwargs={
                'title': 'Shift Ended',
                'message': f'The shift {shift.name} has ended. Please rate the hotel',
                'email': user.email
            })

    db.close()


def send_cancellation_notification(db: Session, user_id: int, title: str, message: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    crud.save_notification(db, title, message, user_id)
    notification.send_firebase_auto_push_notification.apply_async(kwargs={
        'title': title,
        'message': message,
        'user_id': user_id
    })
    email.send_email_auto_notification.apply_async(args=[
        title,
        message,
        user.email
    ])


def suspend_user(db: Session, user_id: int):
    user = crud.get_user_by_id(db, user_id)
    user.is_active = False
    db.add(user)
    db.commit()

    contractor = crud.get_contractor_by_user_id(db, user.id)
    contractor.verified = False
    db.add(contractor)
    db.commit()


def send_manager_notification(db: Session, shift: models.Shifts, type: str):
    manager_user = crud.get_user_by_id(db, shift.createdBy)
    notification_settings = crud.get_notification_setting(db, manager_user)
    if type == constants.SHIFT_CANCEL:
        if notification_settings.email:
            email.send_email_auto_notification.apply_async(kwargs={
                'title': f'Shift Cancelled',
                'message': f'The Shift {shift.name} has been cancelled',
                'email': manager_user.email
            })
        if notification_settings.push:
            notification.send_firebase_push_with_payload.apply_async(kwargs={
                'user_id': manager_user.id,
                'title': f'Shift Cancelled',
                'message': f'The Shift {shift.name} has been cancelled',
                'payload': {
                    'shift_id': shift.id,
                    'hotel_id': shift.hotel_id
                }
            })

    elif type == constants.SHIFT_END:
        if notification_settings.email:
            email.send_email_auto_notification.apply_async(kwargs={
                'title': f'Shift Ended',
                'message': f'The Shift {shift.name} has ended',
                'email': manager_user.email
            })
        if notification_settings.push:
            notification.send_firebase_push_with_payload.apply_async(kwargs={
                'user_id': manager_user.id,
                'title': f'Shift Ended',
                'message': f'The Shift {shift.name} has ended',
                'payload': {
                    'shift_id': shift.id,
                    'hotel_id': shift.hotel_id
                }
            })

    elif type == constants.SHIFT_BEGIN:
        if notification_settings.email:
            email.send_email_auto_notification.apply_async(kwargs={
                'title': f'Shift Started',
                'message': f'The Shift {shift.name} has began',
                'email': manager_user.email
            })
        if notification_settings.push:
            notification.send_firebase_push_with_payload.apply_async(kwargs={
                'user_id': manager_user.id,
                'title': f'Shift Started',
                'message': f'The Shift {shift.name} has began',
                'payload': {
                    'shift_id': shift.id,
                    'hotel_id': shift.hotel_id
                }
            })

    elif type == constants.SHIFT_ACCEPT:
        if notification_settings.email:
            email.send_email_auto_notification.apply_async(kwargs={
                'title': f'Shift Accepted',
                'message': f'The Shift {shift.name} has been accepted',
                'email': manager_user.email
            })
        if notification_settings.push:
            notification.send_firebase_push_with_payload.apply_async(kwargs={
                'user_id': manager_user.id,
                'title': f'Shift Accepted',
                'message': f'The Shift {shift.name} has been accepted',
                'payload': {
                    'shift_id': shift.id,
                    'hotel_id': shift.hotel_id
                }
            })

    else:
        if notification_settings.email:
            email.send_email_auto_notification.apply_async(kwargs={
                'title': f'Shift Declined',
                'message': f'The Shift {shift.name} has been rejected',
                'email': manager_user.email
            })
        if notification_settings.push:
            notification.send_firebase_push_with_payload.apply_async(kwargs={
                'user_id': manager_user.id,
                'title': f'Shift Declined',
                'message': f'The Shift {shift.name} has been rejected',
                'payload': {
                    'shift_id': shift.id,
                    'hotel_id': shift.hotel_id
                }
            })
