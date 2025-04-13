import logging

from tasks_worker import celery_worker


@celery_worker.task(name='ping')
def ping(*args, **kwargs):
    logging.info('OK')
    return 'PONG'
