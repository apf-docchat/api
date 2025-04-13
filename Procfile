api: FLASK_APP=api_cors FLASK_RUN_PORT=5000 flask run
tasks-worker: celery --app=tasks_worker worker --loglevel=info
internal-api: FLASK_APP=internal_api FLASK_RUN_PORT=5001 flask run
instance-manager: FLASK_APP=instance_manager FLASK_RUN_PORT=5002 flask run
qa-tool: FLASK_APP=qa_tool FLASK_RUN_PORT=5003 flask run
