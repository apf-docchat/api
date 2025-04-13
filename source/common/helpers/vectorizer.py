import logging

from source.common import vectorizer_client

logger = logging.getLogger('app')


def _queue_vectorizer_task(task_name: str, org_id: str, filename: str) -> str:
    """Helper function to send tasks to vectorizer"""
    task_params = {
        'source_type': 'local_file',
        'filename': filename,
        'org_id': org_id
    }

    if task_name == 'vectorize':
        logger.info(f"Sending vectorize task to vectorizer with params: {task_params}")

    try:
        task = vectorizer_client.send_task(task_name, kwargs=task_params)
        return task.id
    except Exception as e:
        logger.error(f"Error sending {task_name} task: {e}")
        raise e


def vectorizer_vectorize(org_id: str, filename: str) -> str:
    """Notify vectorizer to add a file for processing"""
    return _queue_vectorizer_task('vectorize', org_id, filename)


def vectorizer_populate_general_metadata(org_id: str, filename: str) -> str:
    """Notify vectorizer to add a file for processing"""
    return _queue_vectorizer_task('populate_general_metadata', org_id, filename)


def vectorizer_remove(org_id: str, filename: str) -> str:
    """Notify vectorizer to remove a file"""
    return _queue_vectorizer_task('remove', org_id, filename)
