import logging

from tasks_worker import celery_worker


@celery_worker.task(name='datasource_db_pull')
def datasource_db_pull(*args, **kwargs):
    logging.info('Started datasource_db_pull task')

    # Loop over each org
    # Get the orgs which have a DB datasource
    # Check if the datasource's schedule is due to run in the next hour
    # Query the DB with the parameters of the datasource
    # Save it to disk using OrgData storage adapter
    # Update the last run timestamp of the datasource

    return 'OK'
