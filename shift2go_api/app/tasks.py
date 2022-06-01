from app.celery_config.celery_app import celery_app


@celery_app.task(name='example_task')
def example_task(word: str) -> str:
    return f"test task returns {word}"

@celery_app.task(name='send_message')
def send_message(word: str) -> str:
    return f"test task returns {word}"
