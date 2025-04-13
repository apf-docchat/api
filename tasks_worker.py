import os

from celery import Celery


class CeleryConfig:
    timezone = 'UTC'

    imports = ('source.tasks',)

    worker_prefetch_multiplier = 1
    worker_max_tasks_per_child = 100
    worker_max_memory_per_child = 800 * 1000  # 800 MB

    task_time_limit = 600  # 10mins

    worker_send_task_events = True
    task_send_sent_event = True

    broker_transport_options = {
        'priority_steps': list(range(10)),
        'queue_order_strategy': 'priority',
    }

    mongodb_backend_settings = {
        'taskmeta_collection': 'tasks_celery_meta',
    }


celery_worker = Celery('tasks',
                       broker=os.getenv('TASKS_CELERY_BROKER_URI'),
                       backend=os.getenv('TASKS_CELERY_RESULT_BACKEND_URI'))

celery_worker.config_from_object(CeleryConfig)

if __name__ == '__main__':
    celery_worker.worker_main()
