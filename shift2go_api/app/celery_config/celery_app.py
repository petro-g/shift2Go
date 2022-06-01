from celery import Celery
from app.config import config
import time
from app.db import models
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal


celery_app = Celery(
    __name__, 
    include=[
        'app.celery_config.tasks.notification',
        'app.celery_config.tasks.email',
        'app.celery_config.tasks.utils'
    ]
)
celery_app.conf.broker_url = config.CELERY_BROKER_URL
celery_app.conf.result_backend = config.CELERY_RESULT_BACKEND


@celery_app.task(name='example_task')
def example_task(word: str) -> str:
    return f"test task returns {word}"


@celery_app.task(name='new_message')
def new_message() -> str:
    db = SessionLocal()
    try:
        admin = db.query(models.User).first()
        db.close()
        obj = admin.__dict__
        del obj['_sa_instance_state']
        return obj
    except Exception as error:
        pass
