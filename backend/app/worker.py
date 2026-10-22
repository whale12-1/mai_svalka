from celery import Celery
from .config import settings

celery_app = Celery("hub", broker=settings.redis_url, backend=settings.redis_url)

@celery_app.task
def noop():
    return True