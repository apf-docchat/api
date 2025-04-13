from celery import Celery

from source.common import config


vectorizer_client = Celery(broker=config.VECTORIZER_QUEUE_URI)
