import os
from celery import Celery
from celery.schedules import crontab


class CeleryConfig:
    timezone = 'UTC'

    redbeat_redis_url = os.getenv('TASKS_SCHEDULER_REDBEAT_REDIS_URI')

    beat_schedule = {
        'healthcheck': {
            'task': 'ping',
            'schedule': crontab(hour='*'),
        },
        'datasource_db_pull_daily': {
            'task': 'datasource.db.pull',
            'schedule': crontab(hour='*', minute='10')
        },
    }


celery_app = Celery('tasks', broker=os.getenv('TASKS_CELERY_BROKER_URI'))

celery_app.config_from_object(CeleryConfig)

if __name__ == '__main__':
    celery_app.worker_main()
