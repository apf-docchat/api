import json
import random
from flask import Blueprint, Response, jsonify, make_response, request
from source.api.utilities import db_helper, queries
from source.api.utilities.externalapi_helpers import auth_helper, jobs_helper

jobs = Blueprint('jobs', __name__)

@jobs.route('', methods=['GET'])
@auth_helper.token_required
def get_jobs_list():
    try:
        jobs_list = jobs_helper.get_jobs_list()
        return make_response(jsonify({'data': jobs_list, 'message': 'List of jobs fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@jobs.route('/<job_id>', methods=['GET'])
@auth_helper.token_required
def get_jobs(job_id):
    try:
        input_params = request.args.get('input_params')
        job = jobs_helper.get_job(job_id, input_params)
        return make_response(jsonify({'data': job, 'message': 'Job fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
    
@jobs.route('/<job_id>/steps/<step_id>', methods=['GET'])
@auth_helper.token_required
def get_step(job_id, step_id):
    try:
        input_params = request.args.get('input_params')
        job = jobs_helper.get_step(job_id, step_id, input_params)
        return make_response(jsonify({'data': job, 'message': 'Job fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@jobs.route('', methods=['POST'])
@auth_helper.token_required
def add_job():
    try:
        new_job = jobs_helper.add_job()
        return make_response(jsonify({'data': new_job, 'message': 'New Job created successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@jobs.route('/<id>/create-steps', methods=['POST'])
@auth_helper.token_required
def create_steps(id):
    try:
        job = jobs_helper.create_steps(id)
        return make_response(jsonify({'data': job, 'message': 'Steps created!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@jobs.route('/<id>', methods=['PATCH'])
@auth_helper.token_required
def update_job(id):
    try:
        new_job = jobs_helper.update_job(id)
        return make_response(jsonify({'data': new_job, 'message': 'Job updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

""" @jobs.route('/<job_id>/steps/<step_id>', methods=['PATCH'])
@auth_helper.token_required
def update_step(job_id, step_id):
    try:
        new_job = jobs_helper.update_step(job_id, step_id)
        return make_response(jsonify({'data': new_job, 'message': 'Step updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500) """

@jobs.route('/<id>/<username>', methods=['DELETE'])
@auth_helper.token_required
def delete_job(id, username):
    try:
        message = jobs_helper.delete_job(id, username)
        return make_response(jsonify({'data': message, 'message': 'Job deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
